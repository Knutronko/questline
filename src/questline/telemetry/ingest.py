"""Ingest telemetry spools into the run store (FP-G2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from questline.core.store import RunStore
from questline.telemetry.spool import dump_spool, load_spool, validate_spool
from questline.telemetry.summary import compute_summary


def ingest_spool_file(
    store: RunStore,
    path: Path,
    *,
    source: str | None = None,
    run_id: str | None = None,
    replace: bool = True,
) -> dict[str, Any]:
    """Validate a spool file and persist session + events."""
    raw = load_spool(path)
    return ingest_spool_dict(
        store, raw, source=source, run_id=run_id, replace=replace
    )


def ingest_spool_dict(
    store: RunStore,
    data: dict[str, Any],
    *,
    source: str | None = None,
    run_id: str | None = None,
    replace: bool = True,
) -> dict[str, Any]:
    """Validate an in-memory spool and persist session + events."""
    spool = validate_spool(data)
    session = spool["session"]
    if source:
        session["source"] = source
    if run_id:
        session["run_id"] = run_id
    events = spool["events"]
    summary = compute_summary(
        events,
        outcome=session.get("outcome"),
        dropped_count=int(session.get("dropped_count") or 0),
    )
    if summary.get("outcome") and not session.get("outcome"):
        session["outcome"] = summary["outcome"]
    artifact = store.save_telemetry_session(
        session=session,
        events=events,
        summary=summary,
        replace=replace,
    )
    dump_spool(
        {"schema_version": spool["schema_version"], "session": session, "events": events},
        artifact,
    )
    return {
        "id": session["id"],
        "game_version": session["game_version"],
        "artifact_path": str(artifact),
        "event_count": len(events),
        "summary": summary,
    }


def parse_drain_payload(raw: Any) -> dict[str, Any]:
    """Coerce DrainTelemetry hook result to ``{session, events, dropped_count}``."""
    payload = _as_dict(raw)
    if payload is None:
        return {"session": None, "events": [], "dropped_count": 0}
    events = payload.get("events")
    if not isinstance(events, list):
        events = []
    dropped = payload.get("dropped_count", 0)
    if not isinstance(dropped, int) or dropped < 0:
        dropped = 0
    session = payload.get("session")
    if session is not None and not isinstance(session, dict):
        session = None
    return {"session": session, "events": events, "dropped_count": dropped}


def _as_dict(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None
