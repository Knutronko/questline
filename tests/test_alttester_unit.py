"""Unit tests for AltTesterDriver with a mocked transport (CI-green)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from questline.core.errors import (
    AuthoringError,
    ElementNotFoundError,
    InfraError,
    SessionLostError,
    Verdict,
    classify,
)
from questline.core.waits import WaitPolicy
from questline.drivers.alttester import AltTesterDriver, compile_locator
from questline.drivers.alttester.errors import map_alttester_error
from questline.drivers.alttester.fake import FakeAltDriverHarness, fake_transport_factory
from questline.drivers.alttester.hooks import parse_hooks_manifest
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.port import ConnectionTarget, GameHook, Point


def test_compile_locator_strategies() -> None:
    q = compile_locator(Locator(by=LocatorStrategy.NAME, value="Play"))
    assert q.by == "NAME"
    assert q.value == "Play"


def test_map_no_app_and_disconnect() -> None:
    class NoAppConnected(Exception):
        pass

    class AppDisconnectedError(Exception):
        close_code = 4002

    assert isinstance(map_alttester_error(NoAppConnected("x")), InfraError)
    lost = map_alttester_error(AppDisconnectedError("gone"))
    assert isinstance(lost, SessionLostError)
    assert classify(lost) is Verdict.INFRA
    assert lost.close_code == 4002


def test_map_not_found() -> None:
    class NotFoundException(Exception):
        pass

    assert isinstance(map_alttester_error(NotFoundException("missing")), ElementNotFoundError)


def test_map_authoring_and_connection_names() -> None:
    class InvalidPathException(Exception):
        pass

    class ConnectionTimeoutError(Exception):
        pass

    class WaitTimeOutException(Exception):
        pass

    assert isinstance(map_alttester_error(InvalidPathException("bad")), AuthoringError)
    assert isinstance(map_alttester_error(ConnectionTimeoutError("t")), InfraError)
    assert isinstance(map_alttester_error(WaitTimeOutException("w")), ElementNotFoundError)


def test_parse_hooks_manifest_errors() -> None:
    with pytest.raises(InfraError, match="not valid JSON"):
        parse_hooks_manifest("{")
    with pytest.raises(AuthoringError, match="hooks"):
        parse_hooks_manifest("{}")
    with pytest.raises(AuthoringError, match="non-empty"):
        parse_hooks_manifest('{"hooks":[{"name":""}]}')


def test_parse_hooks_manifest_roundtrip() -> None:
    raw = {
        "hooks": [
            {
                "name": "SetLevel",
                "args": [{"name": "level", "type": "int"}],
                "causesSoftReload": False,
                "feature": "progression",
            },
            {"name": "Reload", "args": [], "causesSoftReload": True},
        ]
    }
    entries = parse_hooks_manifest(json.dumps(raw))
    assert len(entries) == 2
    assert entries[0].name == "SetLevel"
    assert entries[0].args[0].type == "int"
    assert entries[0].feature == "progression"
    assert entries[1].causes_soft_reload is True


def test_connect_platforms_and_unsupported() -> None:
    state: dict[str, Any] = {}
    d = AltTesterDriver(
        transport_factory=fake_transport_factory(state=state),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    d.connect(ConnectionTarget(platform="editor"))
    assert d.is_alive()
    d.disconnect()
    assert d.is_alive() is False

    d2 = AltTesterDriver(
        transport_factory=fake_transport_factory(state={}),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    with pytest.raises(AuthoringError, match="unsupported"):
        d2.connect(ConnectionTarget(platform="console"))


def test_find_hierarchy_screenshot_interactions() -> None:
    harness = FakeAltDriverHarness(sleeper=lambda _s: None)
    d = harness()
    d.connect(ConnectionTarget(platform="editor"))
    el = d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"))
    assert el.name == "OkButton"
    found = d.find_all(Locator(by=LocatorStrategy.NAME, value="OkButton"))
    assert len(found) == 1
    snap = d.hierarchy()
    assert snap.roots
    assert snap.scene == "FakeScene"
    data = d.screenshot()
    assert data.startswith(b"\x89PNG")
    d.tap(el)
    d.press(Point(1, 2), duration=0.01)
    d.swipe(Point(0, 0), Point(5, 5), duration=0.01)
    d.text_input(el, "typed")
    state = d.app_state()
    assert state.scene == "FakeScene"
    d.disconnect()


def test_find_miss_and_wait_budgets() -> None:
    harness = FakeAltDriverHarness(sleeper=lambda _s: None)
    d = harness()
    d.connect(ConnectionTarget())
    with pytest.raises(ElementNotFoundError):
        d.find(Locator(by=LocatorStrategy.ID, value="nope"))
    policy = WaitPolicy(probe=0.05, deadline=0.1, interval=0.05)
    with pytest.raises(ElementNotFoundError, match="deadline"):
        d.find(Locator(by=LocatorStrategy.ID, value="nope"), policy, budget="deadline")
    with pytest.raises(ElementNotFoundError, match="probe"):
        d.find(Locator(by=LocatorStrategy.ID, value="nope"), policy, budget="probe")
    d.disconnect()


def test_hooks_manifest_and_call_game_method() -> None:
    harness = FakeAltDriverHarness(sleeper=lambda _s: None)
    d = harness()
    d.connect(ConnectionTarget(platform="editor"))
    manifest = d.hooks_manifest()
    names = {e.name for e in manifest}
    assert "GetManifestProbe" in names
    assert "SoftReload" in names
    soft = next(e for e in manifest if e.name == "SoftReload")
    assert soft.causes_soft_reload is True
    result = d.call_game_method(GameHook(name="GetManifestProbe"))
    assert result == "ok"
    d.disconnect()


def test_soft_reload_rehandshake() -> None:
    state: dict[str, Any] = {}
    d = AltTesterDriver(
        transport_factory=fake_transport_factory(state=state),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    d.connect(ConnectionTarget(platform="editor"))
    assert state["connects"] == 1
    # Warm manifest so SoftReload is known to cause soft reload without GameHook flag.
    d.hooks_manifest()
    d.call_game_method(GameHook(name="SoftReload"))
    assert state["connects"] == 2
    assert d.is_alive()
    # Following step succeeds after re-handshake.
    el = d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"))
    assert el.id == "btn_ok"
    d.disconnect()


def test_soft_reload_via_gamehook_flag() -> None:
    state: dict[str, Any] = {}
    d = AltTesterDriver(
        transport_factory=fake_transport_factory(state=state),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    d.connect(ConnectionTarget(platform="editor"))
    d.call_game_method(GameHook(name="SoftReload", causes_soft_reload=True))
    assert state["connects"] == 2
    d.disconnect()


def test_forced_session_lost() -> None:
    harness = FakeAltDriverHarness(sleeper=lambda _s: None)
    d = harness()
    d.connect(ConnectionTarget())
    d.drop_after_commands(1)
    with pytest.raises(SessionLostError) as excinfo:
        d.screenshot()
    assert classify(excinfo.value) is Verdict.INFRA
    assert d.is_alive() is False
