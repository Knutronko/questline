"""Companion (Editor / standalone) performance collector via game hooks."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from questline.drivers.port import GameHook

logger = logging.getLogger("questline.perf.companion")

# Hook registered by ``QuestlinePerfProvider`` in com.questline.companion.
GET_PERF_SAMPLE_HOOK = GameHook(name="GetPerfSample")

# Canonical companion metric names (also accepted aliases below).
_ALIAS = {
    "fps": "fps",
    "allocated_mb": "allocated_mb",
    "allocated_memory_mb": "allocated_mb",
    "memory": "allocated_mb",
    "draw_calls": "draw_calls",
    "drawcalls": "draw_calls",
}


@dataclass
class CompanionPerfCollector:
    """Query companion ``GetPerfSample`` through a connected driver handle/port."""

    call_hook: Callable[[], Any]
    _warned_missing: bool = field(default=False, init=False, repr=False)

    def collect(self) -> Mapping[str, float]:
        try:
            raw = self.call_hook()
        except Exception as exc:
            if not self._warned_missing:
                logger.warning(
                    "companion GetPerfSample failed (%s): %s — metric unavailable "
                    "(ensure QuestlinePerfProvider.EnsureRegistered / QL-3)",
                    type(exc).__name__,
                    exc,
                )
                self._warned_missing = True
            return {}
        payload = _coerce_payload(raw)
        if payload is None:
            logger.warning(
                "companion GetPerfSample returned unusable payload %r — metric unavailable",
                raw,
            )
            return {}
        out: dict[str, float] = {}
        for key, value in payload.items():
            canon = _ALIAS.get(str(key).lower())
            if canon is None:
                continue
            try:
                out[canon] = float(value)
            except (TypeError, ValueError):
                continue
        return out


def companion_collector_from_driver(driver: Any) -> CompanionPerfCollector:
    """Build a collector that calls ``driver.call_game_method(GetPerfSample)``."""

    def _call() -> Any:
        return driver.call_game_method(GET_PERF_SAMPLE_HOOK)

    return CompanionPerfCollector(call_hook=_call)


def _coerce_payload(raw: Any) -> dict[str, Any] | None:
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
