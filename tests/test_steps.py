"""Scenario step pipeline — build vs run, events, HandleOptional probe."""

from __future__ import annotations

import pytest

from questline.authoring.assertions import expect
from questline.authoring.context import Context
from questline.authoring.steps import (
    AssertThat,
    HandleOptional,
    Save,
    Scenario,
    Tap,
    WaitFor,
)
from questline.core.errors import AssertionFailedError, AuthoringError, ElementNotFoundError
from questline.core.events import EventBus, StepFinished, StepStarted
from questline.core.waits import WaitPolicy
from questline.drivers.handle import DriverHandle
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget


def _scene_with_button(*, popup: bool = False) -> MockScene:
    scene = MockScene()
    root = MockNode(id="root", name="Root")
    btn = MockNode(id="btn", name="Btn", text="Go")
    scene.add(root)
    scene.add(btn, parent=root)
    popped = MockNode(id="popup", name="Popup", visible=popup)
    scene.add(popped)
    btn.on_tap = lambda: None
    popped.on_tap = lambda: setattr(popped, "visible", False)
    return scene


def _ctx(scene: MockScene | None = None) -> Context:
    driver = MockDriver(scene or _scene_with_button())
    driver.connect(ConnectionTarget())
    bus = EventBus()
    return Context(
        driver=DriverHandle(driver),
        bus=bus,
        run_id="run-1",
        test_id="test-1",
        wait_policy=WaitPolicy(probe=0.05, deadline=0.5, interval=0.01),
    )


def test_scenario_emits_step_events_and_does_not_run_before_run() -> None:
    ctx = _ctx()
    events: list[str] = []
    ctx.bus.subscribe(lambda e: events.append(e.type_name))

    ran = {"n": 0}
    scenario = (
        Scenario("flow")
        .step(Tap(Locator(by=LocatorStrategy.ID, value="btn")))
        .call(lambda c: ran.__setitem__("n", ran["n"] + 1))
        .step(AssertThat(expect(1).equals(1)))
    )
    assert ran["n"] == 0
    assert len(scenario.steps) == 3
    scenario.run(ctx)
    assert ran["n"] == 1
    assert events.count("StepStarted") == 3
    assert events.count("StepFinished") == 3


def test_failed_step_records_failed_status() -> None:
    ctx = _ctx()
    finished: list[StepFinished] = []
    ctx.bus.subscribe(lambda e: finished.append(e) if isinstance(e, StepFinished) else None)
    scenario = Scenario("fail").step(
        Tap(Locator(by=LocatorStrategy.ID, value="missing"))
    )
    with pytest.raises(ElementNotFoundError):
        scenario.run(ctx)
    assert finished[-1].status == "failed"


def test_handle_optional_probe_dismisses_or_skips() -> None:
    present = _ctx(_scene_with_button(popup=True))
    HandleOptional(Locator(by=LocatorStrategy.ID, value="popup")).execute(present)
    assert present.driver.find_all(Locator(by=LocatorStrategy.ID, value="popup")) == []

    absent = _ctx(_scene_with_button(popup=False))
    # Must not raise when popup missing.
    HandleOptional(Locator(by=LocatorStrategy.ID, value="popup")).execute(absent)


def test_save_and_assert_predicate_false() -> None:
    ctx = _ctx()
    Scenario("save").step(Save("x", lambda c: 7)).run(ctx)
    assert ctx["x"] == 7
    with pytest.raises(AssertionFailedError):
        AssertThat(lambda c: False).execute(ctx)
    with pytest.raises(AuthoringError):
        Save("", lambda c: 1)


def test_wait_for_and_empty_scenario_name() -> None:
    ctx = _ctx()
    WaitFor(Locator(by=LocatorStrategy.ID, value="btn")).execute(ctx)
    with pytest.raises(AuthoringError):
        Scenario("")


def test_step_started_has_real_name() -> None:
    ctx = _ctx()
    names: list[str] = []

    def on_event(e: object) -> None:
        if isinstance(e, StepStarted):
            names.append(e.name)

    ctx.bus.subscribe(on_event)
    Scenario("buy").step(Tap(Locator(by=LocatorStrategy.ID, value="btn"), name="tap_btn")).run(
        ctx
    )
    assert names == ["buy:tap_btn"]
