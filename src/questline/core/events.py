"""Typed frozen events and synchronous in-process pub/sub (architecture §2.2)."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("questline.events")

Subscriber = Callable[["Event"], None]


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Event:
    """Base event. All meaningful run activity emits a typed subclass."""

    run_id: str
    timestamp: datetime = field(default_factory=_utcnow)
    tags: dict[str, str] = field(default_factory=dict)

    @property
    def type_name(self) -> str:
        return type(self).__name__

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["type"] = self.type_name
        data["timestamp"] = self.timestamp.isoformat()
        return data


@dataclass(frozen=True, slots=True)
class RunStarted(Event):
    profile: str = ""


@dataclass(frozen=True, slots=True)
class RunFinished(Event):
    status: str = "passed"
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class TestStarted(Event):
    __test__ = False  # not a pytest test class
    test_id: str = ""
    nodeid: str = ""
    feature_id: str | None = None


@dataclass(frozen=True, slots=True)
class TestFinished(Event):
    __test__ = False  # not a pytest test class
    test_id: str = ""
    nodeid: str = ""
    status: str = "passed"
    verdict: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class StepStarted(Event):
    test_id: str = ""
    step_id: str = ""
    name: str = ""


@dataclass(frozen=True, slots=True)
class StepFinished(Event):
    test_id: str = ""
    step_id: str = ""
    name: str = ""
    status: str = "passed"
    error_message: str | None = None
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class DriverRecovered(Event):
    strategy: str = ""
    duration_s: float | None = None


@dataclass(frozen=True, slots=True)
class SessionLost(Event):
    kind: str = "unknown"
    close_code: int | None = None


@dataclass(frozen=True, slots=True)
class ArtifactSaved(Event):
    test_id: str | None = None
    path: str = ""
    kind: str = "file"
    size_bytes: int = 0


@dataclass(frozen=True, slots=True)
class AiCallMade(Event):
    provider: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    purpose: str = ""
    duration_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class PerfSample(Event):
    test_id: str | None = None
    metric: str = ""
    value: float = 0.0


class EventBus:
    """Synchronous pub/sub. Subscriber errors are isolated and logged loudly."""

    def __init__(self) -> None:
        self._subs: dict[type[Event] | None, list[Subscriber]] = defaultdict(list)

    def subscribe(
        self,
        handler: Subscriber,
        event_type: type[Event] | None = None,
    ) -> None:
        """Register *handler* for *event_type*, or all events when type is None."""
        self._subs[event_type].append(handler)

    def unsubscribe(
        self,
        handler: Subscriber,
        event_type: type[Event] | None = None,
    ) -> None:
        handlers = self._subs.get(event_type)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            return

    def publish(self, event: Event) -> None:
        seen: set[int] = set()
        for key in (type(event), None):
            for handler in list(self._subs.get(key, ())):
                hid = id(handler)
                if hid in seen:
                    continue
                seen.add(hid)
                try:
                    handler(event)
                except Exception:
                    logger.exception(
                        "event subscriber %r failed on %s (isolated; run continues)",
                        handler,
                        event.type_name,
                    )
