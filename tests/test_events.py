"""Event bus tests."""

from __future__ import annotations

import logging

from questline.core.events import EventBus, RunStarted, StepStarted


def test_publish_delivers_to_typed_and_wildcard_subscribers() -> None:
    bus = EventBus()
    seen: list[str] = []

    bus.subscribe(lambda e: seen.append(f"wild:{e.type_name}"))
    bus.subscribe(lambda e: seen.append(f"run:{e.type_name}"), RunStarted)

    bus.publish(RunStarted(run_id="r1", profile="editor"))
    bus.publish(StepStarted(run_id="r1", test_id="t1", step_id="s1", name="tap"))

    assert "wild:RunStarted" in seen
    assert "run:RunStarted" in seen
    assert "wild:StepStarted" in seen
    assert "run:StepStarted" not in seen
    assert seen.index("run:RunStarted") < seen.index("wild:StepStarted")


def test_subscriber_error_is_isolated(caplog) -> None:
    bus = EventBus()
    ok: list[str] = []

    def bad(_event: object) -> None:
        raise RuntimeError("reporter exploded")

    bus.subscribe(bad)
    bus.subscribe(lambda e: ok.append(e.type_name))

    with caplog.at_level(logging.ERROR, logger="questline.events"):
        bus.publish(RunStarted(run_id="r1", profile="x"))

    assert ok == ["RunStarted"]
    assert any("subscriber" in r.message for r in caplog.records)


def test_unsubscribe() -> None:
    bus = EventBus()
    seen: list[str] = []

    def handler(event: object) -> None:
        seen.append(type(event).__name__)

    bus.subscribe(handler)
    bus.unsubscribe(handler)
    bus.unsubscribe(handler)  # idempotent
    bus.publish(RunStarted(run_id="r1", profile="x"))
    assert seen == []


def test_event_tags_default_empty_and_roundtrip() -> None:
    bare = RunStarted(run_id="r1", profile="editor")
    assert bare.tags == {}
    assert bare.to_dict()["tags"] == {}

    tagged = RunStarted(
        run_id="r1",
        profile="editor",
        tags={"feature_id": "feat-42", "source": "scan"},
    )
    payload = tagged.to_dict()
    assert payload["tags"] == {"feature_id": "feat-42", "source": "scan"}
    assert payload["type"] == "RunStarted"
