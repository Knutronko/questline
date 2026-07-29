"""MockDriver unit tests: waits, fault injection, taxonomy."""

from __future__ import annotations

import pytest

from questline.core.errors import SessionLostError, Verdict, classify
from questline.core.waits import WaitPolicy
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget, GameHook


def test_fault_injection_session_lost_is_infra() -> None:
    scene = MockScene()
    scene.add(MockNode(id="a", name="A"))
    driver = MockDriver(scene)
    driver.connect(ConnectionTarget())
    driver.drop_after_commands(2)

    driver.hierarchy()  # command 1 — ok
    with pytest.raises(SessionLostError) as excinfo:
        driver.screenshot()  # command 2 — drops
    err = excinfo.value
    assert err.kind == "fault_inject"
    assert classify(err) is Verdict.INFRA
    assert driver.is_alive() is False


def test_call_game_method_and_app_state() -> None:
    scene = MockScene()
    scene.hooks["GrantCoins"] = lambda n: f"granted:{n}"
    driver = MockDriver(scene)
    driver.connect(ConnectionTarget())
    assert driver.call_game_method(GameHook("GrantCoins"), 5) == "granted:5"
    assert driver.app_state().scene == "MockScene"
    driver.disconnect()


def test_find_respects_probe_budget_faster_than_deadline() -> None:
    """Probe budget must not silently use the longer deadline."""
    clock = {"t": 0.0}

    def now() -> float:
        return clock["t"]

    def sleep(dt: float) -> None:
        clock["t"] += dt

    driver = MockDriver(MockScene(), clock=now, sleeper=sleep)
    driver.connect(ConnectionTarget())
    policy = WaitPolicy(probe=0.2, deadline=10.0, interval=0.1)
    with pytest.raises(Exception, match="probe"):
        driver.find(
            Locator(by=LocatorStrategy.ID, value="missing"),
            policy,
            budget="probe",
        )
    # Should have stopped near probe budget, not deadline.
    assert clock["t"] < 1.0
    driver.disconnect()
