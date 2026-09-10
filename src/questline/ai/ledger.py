"""Persist one ai_calls row (and AiCallMade) per provider attempt."""

from __future__ import annotations

from questline.core.events import AiCallMade, EventBus
from questline.core.store import RunStore


def record_ai_call(
    *,
    store: RunStore | None,
    bus: EventBus | None,
    run_id: str,
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost: float,
    purpose: str,
    duration_ms: float,
    cached: bool = False,
    outcome: str = "ok",
    pricing_version: str = "",
) -> None:
    event = AiCallMade(
        run_id=run_id or "",
        provider=provider,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=cost,
        purpose=purpose,
        duration_ms=duration_ms,
        cached=cached,
        outcome=outcome,
        pricing_version=pricing_version,
    )
    if bus is not None:
        bus.publish(event)
        return
    if store is not None:
        store.on_event(event)
