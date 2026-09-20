"""Read helpers over GameLens store tables (HUD + balance-agent tools)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from questline.core.errors import AuthoringError
from questline.core.store import RunStore
from questline.lens.diff import DiffReport, diff_snapshots
from questline.lens.report import _SUMMARY_KEYS, _is_unset_snapshot, implications_pair_id
from questline.lens.snapshot import load_snapshot

_UNSET_IDS = frozenset({"snap-unset", "unset"})


class SnapshotNotFoundError(KeyError):
    """Unknown snapshot id / game_version."""


def public_path(store: RunStore, path: str | None) -> str | None:
    """Relative to artifacts_dir when possible — avoid leaking home paths."""
    if not path:
        return None
    raw = Path(path)
    try:
        return str(raw.resolve().relative_to(store.artifacts_dir.resolve()))
    except (ValueError, OSError):
        return raw.name


def snapshot_row_public(store: RunStore, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "game_version": row.get("game_version"),
        "git_commit": row.get("git_commit"),
        "feature_id": row.get("feature_id"),
        "created_at": row.get("created_at"),
        "artifact": public_path(store, row.get("artifact_path")),
    }


def list_snapshots_public(store: RunStore, *, limit: int = 100) -> list[dict[str, Any]]:
    return [snapshot_row_public(store, row) for row in store.list_balance_snapshots(limit=limit)]


def resolve_snapshot_row(store: RunStore, key: str) -> dict[str, Any]:
    row = store.get_balance_snapshot(key)
    if row is None:
        raise SnapshotNotFoundError(key)
    return row


def diff_from_store(store: RunStore, key_a: str, key_b: str) -> DiffReport:
    row_a = resolve_snapshot_row(store, key_a)
    row_b = resolve_snapshot_row(store, key_b)
    try:
        snap_a = load_snapshot(Path(str(row_a["artifact_path"])))
        snap_b = load_snapshot(Path(str(row_b["artifact_path"])))
    except AuthoringError:
        raise
    return diff_snapshots(
        snap_a,
        snap_b,
        snapshot_id_a=str(row_a["id"]),
        snapshot_id_b=str(row_b["id"]),
    )


def implications_payload(store: RunStore, pair_id: str) -> dict[str, Any] | None:
    row = store.get_lens_implications(pair_id)
    if row is None:
        return None
    return implications_row_public(store, row, include_body=True)


def implications_for_pair(
    store: RunStore, key_a: str, key_b: str
) -> dict[str, Any] | None:
    try:
        report = diff_from_store(store, key_a, key_b)
    except SnapshotNotFoundError:
        return None
    pair_id = implications_pair_id(report)
    payload = implications_payload(store, pair_id)
    if payload is not None:
        return payload
    rows = store.list_lens_implications(
        snapshot_id_a=report.snapshot_id_a,
        snapshot_id_b=report.snapshot_id_b,
        limit=1,
    )
    if not rows:
        return None
    return implications_row_public(store, rows[0], include_body=True)


def implications_row_public(
    store: RunStore,
    row: dict[str, Any],
    *,
    include_body: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.get("id"),
        "snapshot_id_a": row.get("snapshot_id_a"),
        "snapshot_id_b": row.get("snapshot_id_b"),
        "version_a": row.get("version_a"),
        "version_b": row.get("version_b"),
        "status": row.get("status"),
        "framing": row.get("framing"),
        "prompt_version": row.get("prompt_version"),
        "created_at": row.get("created_at"),
        "artifact": public_path(store, row.get("artifact_path")),
    }
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    out["pending"] = meta.get("pending")
    out["gap_count"] = meta.get("gap_count")
    out["session_count"] = meta.get("session_count")
    out["unjoined_count"] = meta.get("unjoined_count")
    if include_body:
        body = _read_json_artifact(row.get("artifact_path"))
        if body:
            out["summary"] = body.get("summary")
            out["gaps"] = body.get("gaps") or []
            out["measured"] = body.get("measured") or {}
            out["diff_entry_count"] = body.get("diff_entry_count")
            out["pending"] = body.get("pending", out.get("pending"))
    return out


def session_public(row: dict[str, Any], *, include_summary: bool = True) -> dict[str, Any]:
    snapshot_id = row.get("config_snapshot_id")
    outcome = row.get("outcome")
    notes: list[str] = []
    if str(outcome or "").lower() == "lose":
        notes.append("measured play (not a bot/framework fail)")
    if _is_unset_snapshot(snapshot_id) or str(snapshot_id or "").lower() in _UNSET_IDS:
        notes.append("snap-unset: unjoined gap")
    summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
    thin = {k: summary.get(k) for k in _SUMMARY_KEYS if k in summary} if include_summary else {}
    return {
        "id": row.get("id"),
        "game_version": row.get("game_version"),
        "git_commit": row.get("git_commit"),
        "feature_id": row.get("feature_id"),
        "config_snapshot_id": snapshot_id,
        "policy_id": row.get("policy_id"),
        "seed": row.get("seed"),
        "outcome": outcome,
        "source": row.get("source"),
        "run_id": row.get("run_id"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "notes": notes,
        "summary": thin,
    }


def list_sessions_public(
    store: RunStore,
    *,
    config_snapshot_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    rows = store.list_telemetry_sessions(
        config_snapshot_id=config_snapshot_id, limit=limit
    )
    return [session_public(row) for row in rows]


def _read_json_artifact(path: Any) -> dict[str, Any] | None:
    if not path:
        return None
    target = Path(str(path))
    if not target.is_file():
        return None
    try:
        import json

        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None
