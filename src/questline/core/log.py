"""Structured logging helpers (stdlib logging + optional JSON formatter)."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from questline.core.events import Event, EventBus


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("event_type", "run_id", "test_id", "step_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)


def configure_logging(*, json_logs: bool = False, level: int = logging.INFO) -> None:
    """Configure the ``questline`` logger hierarchy once."""
    root = logging.getLogger("questline")
    root.handlers.clear()
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root.addHandler(handler)
    root.propagate = False


def attach_event_logging(bus: EventBus, logger: logging.Logger | None = None) -> None:
    """Subscribe so every bus event is also written to the logger."""
    log = logger or logging.getLogger("questline.events")

    def _on_event(event: Event) -> None:
        extra = {
            "event_type": event.type_name,
            "run_id": event.run_id,
        }
        data = event.to_dict()
        if "test_id" in data:
            extra["test_id"] = data["test_id"]
        if "step_id" in data:
            extra["step_id"] = data["step_id"]
        log.info("event %s", event.type_name, extra=extra)

    bus.subscribe(_on_event)
