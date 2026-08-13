"""Run store: SQLite + artifacts + JSONL ledger (architecture §2.3)."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from questline.core.events import (
    AiCallMade,
    ArtifactSaved,
    Event,
    EventBus,
    PerfSample,
    RunFinished,
    RunStarted,
    StepFinished,
    StepStarted,
    TestFinished,
    TestStarted,
)
from questline.core.migrations import (
    CURRENT_SCHEMA_VERSION,
    apply_migrations,
    get_schema_version,
)


def _ts(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _json_obj(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}


class RunStore:
    """Incremental transactional persistence driven by the event bus."""

    def __init__(
        self,
        db_path: Path,
        *,
        artifacts_dir: Path | None = None,
        ledger_path: Path | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.artifacts_dir = (
            Path(artifacts_dir) if artifacts_dir else self.db_path.parent / "artifacts"
        )
        self.ledger_path = (
            Path(ledger_path) if ledger_path else self.db_path.parent / "ledger.jsonl"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, isolation_level=None
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        apply_migrations(self._conn)
        self._bus: EventBus | None = None

    @property
    def schema_version(self) -> int:
        with self._lock:
            return get_schema_version(self._conn)

    def attach(self, bus: EventBus) -> None:
        """Subscribe to *bus* so every event is persisted incrementally."""
        if self._bus is not None:
            self._bus.unsubscribe(self.on_event)
        self._bus = bus
        bus.subscribe(self.on_event)

    def detach(self) -> None:
        """Unsubscribe from the attached bus without closing the database."""
        if self._bus is not None:
            self._bus.unsubscribe(self.on_event)
            self._bus = None

    def close(self) -> None:
        self.detach()
        with self._lock:
            self._conn.close()

    def on_event(self, event: Event) -> None:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._write_event_row(event)
                self._apply_event(event)
                self._append_ledger(event)
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise

    def save_artifact(
        self,
        data: bytes,
        *,
        run_id: str,
        name: str,
        kind: str = "file",
        test_id: str | None = None,
        bus: EventBus | None = None,
    ) -> Path:
        """Write bytes under artifacts/, emit ArtifactSaved when *bus* is provided."""
        safe_name = name.replace("\\", "/").split("/")[-1]
        dest_dir = self.artifacts_dir / run_id
        if test_id:
            safe_test = (
                test_id.replace("\\", "_").replace("/", "_").replace(":", "_")
            )
            dest_dir = dest_dir / safe_test
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / safe_name
        path.write_bytes(data)
        event = ArtifactSaved(
            run_id=run_id,
            test_id=test_id,
            path=str(path),
            kind=kind,
            size_bytes=len(data),
        )
        target = bus or self._bus
        if target is not None:
            target.publish(event)
        else:
            self.on_event(event)
        return path

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def list_runs(
        self,
        *,
        profile: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return runs newest-first with optional profile/status filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if profile:
            clauses.append("profile = ?")
            params.append(profile)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT * FROM runs {where} ORDER BY started_at DESC LIMIT ? OFFSET ?"
        )
        params.extend([max(0, int(limit)), max(0, int(offset))])
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def list_perf_samples(
        self,
        *,
        run_id: str | None = None,
        test_id: str | None = None,
        metric: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return perf_samples rows (oldest-first) with optional filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if test_id:
            clauses.append("test_id = ?")
            params.append(test_id)
        if metric:
            clauses.append("metric = ?")
            params.append(metric)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT id, run_id, test_id, metric, value, timestamp "
            f"FROM perf_samples {where} ORDER BY id ASC"
        )
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(0, int(limit)))
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def list_artifacts(
        self,
        *,
        run_id: str | None = None,
        test_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List ArtifactSaved payloads from the events table."""
        clauses = ["type = ?"]
        params: list[Any] = ["ArtifactSaved"]
        if run_id:
            clauses.append("run_id = ?")
            params.append(run_id)
        if test_id:
            clauses.append("test_id = ?")
            params.append(test_id)
        sql = (
            "SELECT payload FROM events WHERE "
            + " AND ".join(clauses)
            + " ORDER BY id"
        )
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row["payload"])
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                out.append(payload)
        return out

    def list_tests(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tests WHERE run_id = ? ORDER BY started_at",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_tests_by_nodeid(self, nodeid: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """History of a test identity across runs (newest first)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tests WHERE nodeid = ? ORDER BY started_at DESC LIMIT ?",
                (nodeid, max(0, int(limit))),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_steps(self, test_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM steps WHERE test_id = ? ORDER BY started_at, id",
                (test_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def timeline(self, run_id: str) -> list[dict[str, Any]]:
        """Reconstruct a run timeline: tests with nested steps and real timestamps."""
        tests = self.list_tests(run_id)
        out: list[dict[str, Any]] = []
        for test in tests:
            steps = self.list_steps(test["id"])
            out.append({**test, "steps": steps})
        return out

    def get_test(self, test_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM tests WHERE id = ?", (test_id,)).fetchone()
        return dict(row) if row else None

    def death_point(self, test_id: str) -> dict[str, Any]:
        """Return last-started / last-finished step plus driver health tags for a test.

        Driver health is expected in the most recent TestFinished event's ``tags``
        (written by the authoring plugin on failure). Missing data yields nulls —
        never invented values.
        """
        test = self.get_test(test_id)
        steps = self.list_steps(test_id)
        last_started = steps[-1] if steps else None
        finished = [s for s in steps if s.get("finished_at")]
        last_finished = finished[-1] if finished else None

        driver_health: dict[str, Any] | None = None
        with self._lock:
            row = self._conn.execute(
                "SELECT payload FROM events WHERE test_id = ? AND type = ? "
                "ORDER BY id DESC LIMIT 1",
                (test_id, "TestFinished"),
            ).fetchone()
        if row is not None:
            payload = json.loads(row["payload"])
            tags = payload.get("tags") or {}
            if tags:
                driver_health = dict(tags)

        return {
            "test": test,
            "last_started_step": last_started,
            "last_finished_step": last_finished,
            "driver_health": driver_health,
        }

    def count_events(self, run_id: str | None = None) -> int:
        with self._lock:
            if run_id is None:
                row = self._conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
            else:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS c FROM events WHERE run_id = ?",
                    (run_id,),
                ).fetchone()
        return int(row["c"]) if row else 0

    def _write_event_row(self, event: Event) -> None:
        payload = event.to_dict()
        test_id = payload.get("test_id")
        step_id = payload.get("step_id")
        self._conn.execute(
            "INSERT INTO events (run_id, test_id, step_id, type, timestamp, payload) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.run_id,
                test_id,
                step_id,
                event.type_name,
                _ts(event.timestamp),
                json.dumps(payload, default=str),
            ),
        )

    def _append_ledger(self, event: Event) -> None:
        line = json.dumps(event.to_dict(), default=str)
        with self.ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()

    def _apply_event(self, event: Event) -> None:
        if isinstance(event, RunStarted):
            meta: dict[str, Any] = {}
            if event.tags:
                for key in ("driver", "device"):
                    val = event.tags.get(key)
                    if val:
                        meta[key] = val
            self._conn.execute(
                "INSERT OR REPLACE INTO runs (id, profile, started_at, finished_at, status, meta) "
                "VALUES (?, ?, ?, NULL, ?, ?)",
                (
                    event.run_id,
                    event.profile,
                    _ts(event.timestamp),
                    "running",
                    json.dumps(meta),
                ),
            )
        elif isinstance(event, RunFinished):
            self._conn.execute(
                "UPDATE runs SET finished_at = ?, status = ? WHERE id = ?",
                (_ts(event.timestamp), event.status, event.run_id),
            )
        elif isinstance(event, TestStarted):
            cols = (
                "id, run_id, nodeid, started_at, finished_at, status, "
                "verdict, error_type, error_message, feature_id"
            )
            self._conn.execute(
                f"INSERT OR REPLACE INTO tests ({cols}) "
                "VALUES (?, ?, ?, ?, NULL, ?, NULL, NULL, NULL, ?)",
                (
                    event.test_id,
                    event.run_id,
                    event.nodeid,
                    _ts(event.timestamp),
                    "running",
                    event.feature_id,
                ),
            )
        elif isinstance(event, TestFinished):
            self._conn.execute(
                "UPDATE tests SET finished_at = ?, status = ?, verdict = ?, error_type = ?, "
                "error_message = ? WHERE id = ?",
                (
                    _ts(event.timestamp),
                    event.status,
                    event.verdict,
                    event.error_type,
                    event.error_message,
                    event.test_id,
                ),
            )
        elif isinstance(event, StepStarted):
            step_cols = "id, test_id, run_id, name, started_at, finished_at, status, error_message"
            self._conn.execute(
                f"INSERT OR REPLACE INTO steps ({step_cols}) VALUES (?, ?, ?, ?, ?, NULL, ?, NULL)",
                (
                    event.step_id,
                    event.test_id,
                    event.run_id,
                    event.name,
                    _ts(event.timestamp),
                    "running",
                ),
            )
        elif isinstance(event, StepFinished):
            self._conn.execute(
                "UPDATE steps SET finished_at = ?, status = ?, error_message = ? WHERE id = ?",
                (_ts(event.timestamp), event.status, event.error_message, event.step_id),
            )
        elif isinstance(event, PerfSample):
            self._conn.execute(
                "INSERT INTO perf_samples (run_id, test_id, metric, value, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    event.run_id,
                    event.test_id,
                    event.metric,
                    event.value,
                    _ts(event.timestamp),
                ),
            )
        elif isinstance(event, AiCallMade):
            cols = (
                "run_id, provider, model, tokens_in, tokens_out, "
                "cost, purpose, duration_ms, timestamp"
            )
            self._conn.execute(
                f"INSERT INTO ai_calls ({cols}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event.run_id,
                    event.provider,
                    event.model,
                    event.tokens_in,
                    event.tokens_out,
                    event.cost,
                    event.purpose,
                    event.duration_ms,
                    _ts(event.timestamp),
                ),
            )
        elif isinstance(event, ArtifactSaved):
            # Already in events table; no dedicated artifact table in v0 schema.
            pass

    def save_balance_snapshot(
        self,
        *,
        snapshot_id: str,
        game_version: str,
        payload: bytes | str,
        git_commit: str | None = None,
        feature_id: str | None = None,
        created_at: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Path:
        """Persist a balance_snapshot.json artifact and index row (FP-G1)."""
        data = payload.encode("utf-8") if isinstance(payload, str) else payload
        dest_dir = self.artifacts_dir / "lens" / snapshot_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "balance_snapshot.json"
        path.write_bytes(data)
        ts = created_at or datetime.now().astimezone().isoformat()
        meta_json = json.dumps(meta or {}, sort_keys=True)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO balance_snapshots
                    (id, game_version, git_commit, feature_id, artifact_path, created_at, meta)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_id,
                        game_version,
                        git_commit,
                        feature_id,
                        str(path),
                        ts,
                        meta_json,
                    ),
                )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return path

    def get_balance_snapshot(self, key: str) -> dict[str, Any] | None:
        """Resolve by snapshot id, else latest row for game_version."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM balance_snapshots WHERE id = ?", (key,)
            ).fetchone()
            if row is None:
                row = self._conn.execute(
                    """
                    SELECT * FROM balance_snapshots
                    WHERE game_version = ?
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """,
                    (key,),
                ).fetchone()
        return dict(row) if row else None

    def list_balance_snapshots(
        self,
        *,
        game_version: str | None = None,
        feature_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if game_version:
            clauses.append("game_version = ?")
            params.append(game_version)
        if feature_id:
            clauses.append("feature_id = ?")
            params.append(feature_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT * FROM balance_snapshots {where} "
            f"ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        )
        params.extend([max(0, int(limit)), max(0, int(offset))])
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def save_telemetry_session(
        self,
        *,
        session: dict[str, Any],
        events: list[dict[str, Any]],
        summary: dict[str, Any] | None = None,
        replace: bool = True,
        created_at: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> Path:
        """Persist a telemetry session, events, and spool artifact (FP-G2)."""
        session_id = str(session["id"])
        dest_dir = self.artifacts_dir / "telemetry" / session_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        path = dest_dir / "spool.json"
        ts = created_at or datetime.now().astimezone().isoformat()
        summary_json = json.dumps(summary or {}, sort_keys=True)
        meta_json = json.dumps(meta or {}, sort_keys=True)
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                existing = self._conn.execute(
                    "SELECT id FROM telemetry_sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
                if existing is not None:
                    if not replace:
                        raise ValueError(
                            f"telemetry session already exists: {session_id}"
                        )
                    self._conn.execute(
                        "DELETE FROM telemetry_events WHERE session_id = ?",
                        (session_id,),
                    )
                    self._conn.execute(
                        "DELETE FROM telemetry_sessions WHERE id = ?",
                        (session_id,),
                    )
                self._conn.execute(
                    """
                    INSERT INTO telemetry_sessions (
                        id, game_version, git_commit, feature_id,
                        config_snapshot_id, policy_id, seed, started_at,
                        finished_at, outcome, source, run_id, artifact_path,
                        summary, meta, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        session["game_version"],
                        session.get("git_commit"),
                        session.get("feature_id"),
                        session.get("config_snapshot_id"),
                        session.get("policy_id"),
                        session.get("seed"),
                        session["started_at"],
                        session.get("finished_at"),
                        session.get("outcome"),
                        session["source"],
                        session.get("run_id"),
                        str(path),
                        summary_json,
                        meta_json,
                        ts,
                    ),
                )
                rows = [
                    (
                        session_id,
                        int(ev["seq"]),
                        float(ev["t"]),
                        str(ev["name"]),
                        json.dumps(ev.get("payload") or {}, sort_keys=True),
                    )
                    for ev in events
                ]
                self._conn.executemany(
                    """
                    INSERT INTO telemetry_events
                    (session_id, seq, t, name, payload)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return path

    def get_telemetry_session(self, session_id: str) -> dict[str, Any] | None:
        """Resolve by exact id, else unique prefix match."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM telemetry_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None and session_id:
                matches = self._conn.execute(
                    """
                    SELECT * FROM telemetry_sessions
                    WHERE id LIKE ? ESCAPE '\\'
                    ORDER BY created_at DESC, id DESC
                    """,
                    (session_id.replace("%", "\\%").replace("_", "\\_") + "%",),
                ).fetchall()
                if len(matches) == 1:
                    row = matches[0]
        if row is None:
            return None
        data = dict(row)
        data["summary"] = _json_obj(data.get("summary"))
        data["meta"] = _json_obj(data.get("meta"))
        return data

    def list_telemetry_sessions(
        self,
        *,
        game_version: str | None = None,
        config_snapshot_id: str | None = None,
        policy_id: str | None = None,
        feature_id: str | None = None,
        seed: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if game_version:
            clauses.append("game_version = ?")
            params.append(game_version)
        if config_snapshot_id:
            clauses.append("config_snapshot_id = ?")
            params.append(config_snapshot_id)
        if policy_id:
            clauses.append("policy_id = ?")
            params.append(policy_id)
        if feature_id:
            clauses.append("feature_id = ?")
            params.append(feature_id)
        if seed:
            clauses.append("seed = ?")
            params.append(seed)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = (
            f"SELECT * FROM telemetry_sessions {where} "
            f"ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        )
        params.extend([max(0, int(limit)), max(0, int(offset))])
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            data["summary"] = _json_obj(data.get("summary"))
            data["meta"] = _json_obj(data.get("meta"))
            out.append(data)
        return out

    def list_telemetry_events(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT seq, t, name, payload FROM telemetry_events
                WHERE session_id = ? ORDER BY seq ASC
                """,
                (session_id,),
            ).fetchall()
        events: list[dict[str, Any]] = []
        for row in rows:
            events.append(
                {
                    "seq": int(row["seq"]),
                    "t": float(row["t"]),
                    "name": row["name"],
                    "payload": _json_obj(row["payload"]),
                }
            )
        return events

    def count_telemetry_events(self, session_id: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM telemetry_events WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        return int(row["n"]) if row is not None else 0

    def __enter__(self) -> RunStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = ["CURRENT_SCHEMA_VERSION", "RunStore"]
