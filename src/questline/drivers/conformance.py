"""Parametrized DriverPort conformance suite.

Any real adapter must pass these cases. Provide a zero-arg factory that returns a
fresh, disconnected ``DriverPort``. MockDriver is the reference implementation.

Run against mock::

    pytest tests/test_driver_conformance.py -q

Adapters (Phase 04+) should parametrize ``driver_factory`` the same way.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from questline.core.errors import ElementNotFoundError, SessionLostError, Verdict, classify
from questline.core.waits import WaitPolicy
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.port import ConnectionTarget, DriverPort, Element, Point

DriverFactory = Callable[[], DriverPort]


def _seed_basic_tree(driver: DriverPort) -> None:
    """Best-effort seed for drivers that expose a mock scene.

    Real adapters should already have a game under test; they can no-op here by not
    having ``scene``. Conformance cases that need elements skip when the tree is empty
    after connect — adapters must document their fixture requirements.
    """
    scene = getattr(driver, "scene", None)
    if scene is None:
        return
    from questline.drivers.mock.scene import MockNode

    if scene.get("btn_ok") is not None:
        return
    root = MockNode(id="canvas", name="Canvas", path="/Canvas")
    btn = MockNode(id="btn_ok", name="OkButton", text="OK", path="/Canvas/OkButton")
    label = MockNode(id="lbl_hi", name="Greeting", text="Hello", path="/Canvas/Greeting")
    scene.add(root)
    scene.add(btn, parent=root)
    scene.add(label, parent=root)


def case_connect_alive(factory: DriverFactory) -> None:
    d = factory()
    assert d.is_alive() is False
    d.connect(ConnectionTarget(host="127.0.0.1", port=13000))
    assert d.is_alive() is True
    d.disconnect()
    assert d.is_alive() is False


def case_find_immediate_miss(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    with pytest.raises(ElementNotFoundError):
        d.find(Locator(by=LocatorStrategy.ID, value="does-not-exist"))
    assert classify(ElementNotFoundError("x")) is Verdict.TEST
    d.disconnect()


def case_find_immediate_hit(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    el = d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"))
    assert isinstance(el, Element)
    assert el.id == "btn_ok"
    d.disconnect()


def case_find_deadline_timeout(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    policy = WaitPolicy(probe=0.05, deadline=0.15, interval=0.05)
    with pytest.raises(ElementNotFoundError, match="deadline"):
        d.find(
            Locator(by=LocatorStrategy.ID, value="never"),
            policy,
            budget="deadline",
        )
    d.disconnect()


def case_find_probe_timeout(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    policy = WaitPolicy(probe=0.1, deadline=5.0, interval=0.05)
    with pytest.raises(ElementNotFoundError, match="probe"):
        d.find(
            Locator(by=LocatorStrategy.ID, value="never"),
            policy,
            budget="probe",
        )
    d.disconnect()


def case_find_wait_appear(factory: DriverFactory) -> None:
    d = factory()
    schedule = getattr(d, "schedule_appear", None)
    if schedule is None:
        pytest.skip("driver does not support schedule_appear")
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    schedule("btn_ok", 0.1)
    policy = WaitPolicy(probe=0.05, deadline=1.0, interval=0.05)
    el = d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"), policy, budget="deadline")
    assert el.id == "btn_ok"
    assert el.visible is True
    d.disconnect()


def case_find_all_and_compile(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    loc = Locator(by=LocatorStrategy.NAME, value="OkButton")
    native = d.compile(loc)
    assert native is not None
    found = d.find_all(loc)
    assert len(found) >= 1
    assert found[0].name == "OkButton"
    d.disconnect()


def case_hierarchy_normalized(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    snap = d.hierarchy()
    assert snap.roots
    assert all(isinstance(r.element, Element) for r in snap.roots)
    d.disconnect()


def case_screenshot_bytes(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    data = d.screenshot()
    assert isinstance(data, bytes)
    assert len(data) > 0
    d.disconnect()


def case_interactions(factory: DriverFactory) -> None:
    d = factory()
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    el = d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"))
    d.tap(el)
    d.press(el, duration=0.01)
    d.swipe(Point(0, 0), Point(10, 10), duration=0.01)
    d.text_input(el, "typed")
    # text_input on a button is odd but must be acknowledged without infra errors
    state = d.app_state()
    assert state.foreground is True
    d.disconnect()


def case_forced_disconnect_session_lost(factory: DriverFactory) -> None:
    d = factory()
    force = getattr(d, "force_disconnect", None)
    drop = getattr(d, "drop_after_commands", None)
    if force is None and drop is None:
        pytest.skip("driver has no fault-injection hooks")
    d.connect(ConnectionTarget())
    _seed_basic_tree(d)
    if drop is not None:
        drop(1)
        with pytest.raises(SessionLostError) as excinfo:
            d.screenshot()
        assert classify(excinfo.value) is Verdict.INFRA
        assert d.is_alive() is False
    else:
        force()
        assert d.is_alive() is False
        with pytest.raises(SessionLostError) as excinfo:
            d.screenshot()
        assert classify(excinfo.value) is Verdict.INFRA
    d.disconnect()


CONFORMANCE_CASES: list[Callable[[DriverFactory], Any]] = [
    case_connect_alive,
    case_find_immediate_miss,
    case_find_immediate_hit,
    case_find_deadline_timeout,
    case_find_probe_timeout,
    case_find_wait_appear,
    case_find_all_and_compile,
    case_hierarchy_normalized,
    case_screenshot_bytes,
    case_interactions,
    case_forced_disconnect_session_lost,
]
