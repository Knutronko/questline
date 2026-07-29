"""Logging helpers."""

from __future__ import annotations

import json
import logging

from questline.core.events import EventBus, RunStarted, StepStarted
from questline.core.log import JsonFormatter, attach_event_logging, configure_logging


def test_json_formatter_emits_object() -> None:
    record = logging.LogRecord(
        name="questline.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    record.event_type = "RunStarted"  # type: ignore[attr-defined]
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["event_type"] == "RunStarted"


def test_json_formatter_includes_exc_info() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="questline.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=sys.exc_info(),
        )
    payload = json.loads(JsonFormatter().format(record))
    assert "ValueError" in payload["exc_info"]


def test_configure_logging_json_mode() -> None:
    configure_logging(json_logs=True, level=logging.DEBUG)
    root = logging.getLogger("questline")
    assert root.handlers
    assert isinstance(root.handlers[0].formatter, JsonFormatter)


def test_attach_event_logging(caplog) -> None:
    bus = EventBus()
    log = logging.getLogger("questline.events.attach_test")
    log.handlers.clear()
    log.setLevel(logging.INFO)
    log.propagate = True
    attach_event_logging(bus, logger=log)
    with caplog.at_level(logging.INFO, logger="questline.events.attach_test"):
        bus.publish(RunStarted(run_id="r1", profile="editor"))
        bus.publish(StepStarted(run_id="r1", test_id="t1", step_id="s1", name="tap"))
    assert any("RunStarted" in r.message for r in caplog.records)
    assert any("StepStarted" in r.message for r in caplog.records)
