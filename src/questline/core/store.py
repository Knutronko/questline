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

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    profile TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    meta TEXT
);

CREATE TABLE IF NOT EXISTS tests (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    nodeid TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    status TEXT,
    verdict TEXT,
    error_type TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    test_id TEXT NOT NULL REFERENCES tests(id),
    run_id TEXT NOT NULL,
    name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    test_id TEXT,
    step_id TEXT,
    type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS perf_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    test_id TEXT,
    metric TEXT NOT NULL,
    value REAL NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    provider TEXT,
    model TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost REAL,
    purpose TEXT,
    duration_ms REAL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quarantine (
    test_id TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    entered_at TEXT NOT NULL,
    owner TEXT,
    exit_criteria TEXT,
    linked_issue TEXT,
    left_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_tests_run ON tests(run_id);
CREATE INDEX IF NOT EXISTS idx_steps_test ON steps(test_id);
CREATE INDEX IF NOT EXISTS idx_events_run ON events(run_id);
"""


def _ts(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


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
        self._conn.executescript(_SCHEMA)
        self._bus: EventBus | None = None

    def attach(self, bus: EventBus) -> None:
        """Subscribe to *bus* so every event is persisted incrementally."""
        if self._bus is not None:
            self._bus.unsubscribe(self.on_event)
        self._bus = bus
        bus.subscribe(self.on_event)

    def close(self) -> None:
        if self._bus is not None:
            self._bus.unsubscribe(self.on_event)
            self._bus = None
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
            dest_dir = dest_dir / test_id
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

    def list_tests(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM tests WHERE run_id = ? ORDER BY started_at",
                (run_id,),
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
            self._conn.execute(
                "INSERT OR REPLACE INTO runs (id, profile, started_at, finished_at, status, meta) "
                "VALUES (?, ?, ?, NULL, ?, ?)",
                (event.run_id, event.profile, _ts(event.timestamp), "running", "{}"),
            )
        elif isinstance(event, RunFinished):
            self._conn.execute(
                "UPDATE runs SET finished_at = ?, status = ? WHERE id = ?",
                (_ts(event.timestamp), event.status, event.run_id),
            )
        elif isinstance(event, TestStarted):
            cols = (
                "id, run_id, nodeid, started_at, finished_at, status, "
                "verdict, error_type, error_message"
            )
            self._conn.execute(
                f"INSERT OR REPLACE INTO tests ({cols}) "
                "VALUES (?, ?, ?, ?, NULL, ?, NULL, NULL, NULL)",
                (event.test_id, event.run_id, event.nodeid, _ts(event.timestamp), "running"),
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

    def __enter__(self) -> RunStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
