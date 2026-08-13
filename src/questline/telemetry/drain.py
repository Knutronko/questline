"""Drain companion telemetry over existing Wire ``call_hook`` (no protocol bump)."""

from __future__ import annotations

from typing import Any

from questline.core.store import RunStore
from questline.drivers.port import GameHook
from questline.telemetry.ingest import ingest_spool_dict, parse_drain_payload
from questline.telemetry.schema import DRAIN_BATCH_SIZE, HOOK_DRAIN, HOOK_END_SESSION, SOURCE_WIRE

DRAIN_HOOK = GameHook(name=HOOK_DRAIN)
END_SESSION_HOOK = GameHook(name=HOOK_END_SESSION)


def drain_telemetry(
    driver: Any,
    store: RunStore | None = None,
    *,
    run_id: str | None = None,
    end_outcome: str | None = None,
    max_batches: int = 64,
) -> dict[str, Any]:
    """Pull pending events via ``DrainTelemetry`` and optionally ingest them.

    Call ``EndTelemetrySession`` first when the measured session should close
    (FP-G3). Incremental drains append in the companion; ingest here is a
    **replace** of the session row from the concatenated batches of this call.

    Returns the combined drain payload (session + events). When *store* is set
    and a session envelope with ``game_version`` is present, the spool is
    ingested.
    """
    if end_outcome is not None:
        driver.call_game_method(END_SESSION_HOOK, end_outcome)

    events: list[dict[str, Any]] = []
    session: dict[str, Any] | None = None
    dropped = 0
    for _ in range(max(1, max_batches)):
        raw = driver.call_game_method(DRAIN_HOOK)
        batch = parse_drain_payload(raw)
        if batch["session"] is not None:
            session = batch["session"]
        dropped = int(batch.get("dropped_count") or dropped)
        chunk = [e for e in batch["events"] if isinstance(e, dict)]
        events.extend(chunk)
        if len(chunk) < DRAIN_BATCH_SIZE:
            break

    result: dict[str, Any] = {
        "session": session,
        "events": events,
        "dropped_count": dropped,
    }
    if store is None or session is None:
        return result
    if not session.get("game_version"):
        return result

    envelope = dict(session)
    envelope["source"] = SOURCE_WIRE
    envelope["dropped_count"] = dropped
    if run_id:
        envelope["run_id"] = run_id
    ingested = ingest_spool_dict(
        store,
        {"schema_version": 1, "session": envelope, "events": events},
        source=SOURCE_WIRE,
        run_id=run_id,
        replace=True,
    )
    result["ingested"] = ingested
    return result
