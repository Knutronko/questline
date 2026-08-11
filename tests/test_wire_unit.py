"""Unit + fake-transport tests for QuestlineWire (CI-green, no Unity).

Covers the phase-09b Wire v2 UI matrix (FakeWire) plus MVP hooks regression.
"""

from __future__ import annotations

import json
import socket
import threading
from typing import Any

import pytest

from questline.core.errors import (
    AuthoringError,
    ElementNotFoundError,
    InfraError,
    SessionLostError,
    TestError,
    Verdict,
    classify,
)
from questline.core.waits import WaitPolicy
from questline.drivers.conformance import WIRE_CONFORMANCE_CASES
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.port import ConnectionTarget, Element, GameHook, Point
from questline.drivers.wire import QuestlineDriver
from questline.drivers.wire.codec import element_from_dict, hierarchy_from_dict, png_from_result
from questline.drivers.wire.errors import (
    deferred_gesture_not_implemented,
    error_from_server,
    map_wire_error,
    mvp_ui_not_implemented,
    ui_not_supported,
)
from questline.drivers.wire.fake import (
    FakeUiNode,
    FakeWireDriverHarness,
    FakeWireTransport,
    default_fake_ui_tree,
    fake_transport_factory,
)
from questline.drivers.wire.protocol import (
    ENVELOPE_VERSION,
    PROTOCOL_VERSION,
    hello_advertises_ui,
    make_request,
    parse_response,
)
from questline.drivers.wire.transport import connect_real_transport


def test_protocol_roundtrip() -> None:
    line = make_request("ping", req_id="abc")
    assert '"op":"ping"' in line
    assert '"id":"abc"' in line
    assert f'"v":{ENVELOPE_VERSION}' in line
    data = parse_response('{"v":1,"id":"abc","ok":true,"result":{"pong":true}}')
    assert data["ok"] is True
    assert "find" in make_request("find", {"by": "id", "value": "x"})


def test_error_mapping() -> None:
    assert isinstance(error_from_server("authoring", "bad"), AuthoringError)
    assert isinstance(error_from_server("test", "boom"), TestError)
    assert isinstance(error_from_server("session_lost", "gone"), SessionLostError)
    assert isinstance(error_from_server("element_not_found", "miss"), ElementNotFoundError)
    assert classify(map_wire_error(ConnectionRefusedError("x"))) is Verdict.INFRA
    assert "Wire MVP" in str(mvp_ui_not_implemented())
    assert "UI capability" in str(ui_not_supported())
    assert "press" in str(deferred_gesture_not_implemented("press"))


def test_hello_advertises_ui() -> None:
    assert hello_advertises_ui({"protocol_version": 2, "features": ["hooks", "ui"]})
    assert hello_advertises_ui({"protocol_version": 2})
    assert hello_advertises_ui({"protocol_version": 1, "features": ["hooks", "ui"]})
    assert not hello_advertises_ui({"protocol_version": 1, "features": ["hooks"]})
    assert not hello_advertises_ui({"protocol_version": 1})


def test_connect_platforms_and_unsupported() -> None:
    state: dict[str, Any] = {}
    d = QuestlineDriver(
        transport_factory=fake_transport_factory(state=state),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    d.connect(ConnectionTarget(platform="editor"))
    assert d.is_alive()
    d.disconnect()
    assert d.is_alive() is False

    d2 = QuestlineDriver(
        transport_factory=fake_transport_factory(state={}),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    with pytest.raises(AuthoringError, match="unsupported"):
        d2.connect(ConnectionTarget(platform="console"))


def test_hooks_manifest_and_call() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget(platform="editor"))
    manifest = d.hooks_manifest()
    names = {e.name for e in manifest}
    assert "Ping" in names
    assert d.call_game_method(GameHook(name="Ping")) == "pong"
    state = d.app_state()
    assert state.scene == "FakeWireScene"
    d.disconnect()


def test_soft_reload_rehandshake() -> None:
    state: dict[str, Any] = {}
    d = QuestlineDriver(
        transport_factory=fake_transport_factory(state=state),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    d.connect(ConnectionTarget(platform="editor"))
    assert state["connects"] == 1
    d.hooks_manifest()
    d.call_game_method(GameHook(name="SoftReload"))
    assert state["connects"] == 2
    assert d.is_alive()
    assert d.call_game_method(GameHook(name="Ping")) == "pong"
    d.disconnect()


def test_soft_reload_via_gamehook_flag() -> None:
    state: dict[str, Any] = {}
    d = QuestlineDriver(
        transport_factory=fake_transport_factory(state=state),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    d.connect(ConnectionTarget(platform="editor"))
    d.call_game_method(GameHook(name="GetManifestProbe", causes_soft_reload=True))
    assert state["connects"] == 2
    d.disconnect()


def test_deferred_gestures_authoring_error() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    with pytest.raises(AuthoringError, match="press"):
        d.press(Point(0, 0))
    with pytest.raises(AuthoringError, match="swipe"):
        d.swipe(Point(0, 0), Point(1, 1))
    with pytest.raises(AuthoringError, match="text_input"):
        d.text_input(Element(id="x"), "hi")
    d.disconnect()


def test_hierarchy_roundtrip_and_caps() -> None:
    empty = FakeWireTransport(state={"ui_root": None})
    raw = empty.request("hierarchy", {})
    snap = hierarchy_from_dict(raw)
    assert snap.roots == ()
    assert raw["node_count"] == 0

    deep = FakeUiNode(id="r", name="Root", path="/Root")
    cur = deep
    for i in range(10):
        child = FakeUiNode(id=f"n{i}", name=f"N{i}", path=f"/Root/{i}")
        cur.children.append(child)
        cur = child
    transport = FakeWireTransport(state={"ui_root": deep, "max_depth": 2, "max_nodes": 3})
    raw = transport.request("hierarchy", {"max_depth": 2, "max_nodes": 3})
    assert raw["truncated"] is True
    assert raw["node_count"] <= 3
    snap = hierarchy_from_dict(raw)
    assert snap.roots
    assert snap.roots[0].element.id == "r"


def test_find_strategies_scope_and_miss() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())

    by_id = d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"))
    assert by_id.id == "btn_ok"
    by_name = d.find(Locator(by=LocatorStrategy.NAME, value="Greeting"))
    assert by_name.text == "Hello"
    by_path = d.find(Locator(by=LocatorStrategy.PATH, value="/Canvas/OkButton"))
    assert by_path.name == "OkButton"
    by_text = d.find(Locator(by=LocatorStrategy.TEXT, value="OK"))
    assert by_text.id == "btn_ok"
    by_comp = d.find(Locator(by=LocatorStrategy.COMPONENT, value="Text"))
    assert by_comp.id == "lbl_hi"

    scoped = d.find_all(
        Locator(by=LocatorStrategy.NAME, value="OkButton", scope="/Canvas/Panel")
    )
    assert len(scoped) == 1
    assert scoped[0].id == "btn_nested"

    all_ok = d.find_all(Locator(by=LocatorStrategy.NAME, value="OkButton"))
    assert len(all_ok) >= 2
    first = d.find(Locator(by=LocatorStrategy.NAME, value="OkButton"))
    assert first.id == all_ok[0].id

    with pytest.raises(ElementNotFoundError):
        d.find(Locator(by=LocatorStrategy.ID, value="missing"))

    policy = WaitPolicy(probe=0.05, deadline=0.12, interval=0.05)
    with pytest.raises(ElementNotFoundError, match="deadline"):
        d.find(
            Locator(by=LocatorStrategy.ID, value="never"),
            policy,
            budget="deadline",
        )
    d.disconnect()


def test_tap_element_point_and_stale() -> None:
    state: dict[str, Any] = {}
    d = QuestlineDriver(
        transport_factory=fake_transport_factory(state=state),
        rehandshake_delay_s=0.0,
        sleeper=lambda _s: None,
    )
    d.connect(ConnectionTarget())
    el = d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"))
    d.tap(el)
    root = state["ui_root"]
    assert isinstance(root, FakeUiNode)
    btn = next(n for n in _walk(root) if n.id == "btn_ok")
    assert btn.tapped is True

    d.tap(Point(3.0, 4.0))
    assert (3.0, 4.0) in state["point_taps"]

    with pytest.raises(ElementNotFoundError, match="tap target"):
        d.tap(Element(id="stale-id"))
    d.disconnect()


def test_screenshot_png_and_failure() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    data = d.screenshot()
    assert data[:4] == b"\x89PNG"
    assert len(data) > 0
    d.disconnect()

    fail = FakeWireDriverHarness(state={"screenshot_fail": True})
    d2 = fail()
    d2.connect(ConnectionTarget())
    with pytest.raises(AuthoringError, match="screenshot"):
        d2.screenshot()
    d2.disconnect()

    with pytest.raises(AuthoringError, match="empty"):
        png_from_result({"png_base64": ""})


def test_legacy_companion_no_ui_hooks_still_work() -> None:
    harness = FakeWireDriverHarness(state={"legacy_mvp": True})
    d = harness()
    d.connect(ConnectionTarget())
    assert d.call_game_method(GameHook(name="Ping")) == "pong"
    assert d.app_state().scene == "FakeWireScene"
    with pytest.raises(AuthoringError, match="UI capability"):
        d.hierarchy()
    with pytest.raises(AuthoringError, match="UI capability"):
        d.find(Locator(by=LocatorStrategy.ID, value="x"))
    with pytest.raises(AuthoringError, match="UI capability"):
        d.tap(Point(0, 0))
    with pytest.raises(AuthoringError, match="UI capability"):
        d.screenshot()
    d.disconnect()


def test_disconnect_mid_op_session_lost() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    d.drop_after_commands(1)
    with pytest.raises(SessionLostError) as excinfo:
        d.find(Locator(by=LocatorStrategy.ID, value="btn_ok"))
    assert classify(excinfo.value) is Verdict.INFRA
    assert d.is_alive() is False


def test_compile_and_element_codec() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    q = d.compile(Locator(by=LocatorStrategy.NAME, value="OkButton", scope="/Canvas"))
    assert q.by is LocatorStrategy.NAME
    assert q.to_params()["scope"] == "/Canvas"
    el = element_from_dict(
        {
            "id": "1",
            "name": "A",
            "path": "/A",
            "text": "",
            "visible": True,
            "enabled": True,
            "bounds": [1, 2, 3, 4],
        }
    )
    assert el.bounds == (1.0, 2.0, 3.0, 4.0)
    d.disconnect()


def test_error_from_server_variants() -> None:
    assert isinstance(error_from_server("infra", "x"), InfraError)
    assert isinstance(error_from_server("timeout", "x"), SessionLostError)
    assert isinstance(error_from_server("weird", "x"), InfraError)
    assert isinstance(map_wire_error(TimeoutError("t")), SessionLostError)
    assert isinstance(map_wire_error(OSError("o")), InfraError)
    assert isinstance(map_wire_error(AuthoringError("already")), AuthoringError)


def test_force_disconnect() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    d.force_disconnect()
    assert d.is_alive() is False
    with pytest.raises(SessionLostError):
        d.app_state()


def test_unknown_hook_and_set_level() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    with pytest.raises(AuthoringError, match="unknown"):
        d.call_game_method(GameHook(name="NoSuchHook"))
    d.call_game_method(GameHook(name="SetLevel"), 3)
    d.disconnect()


def test_protocol_unknown_op() -> None:
    with pytest.raises(ValueError, match="unknown wire op"):
        make_request("nope")
    with pytest.raises(ValueError, match="JSON object"):
        parse_response("[]")


def test_forced_session_lost() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    d.drop_after_commands(1)
    with pytest.raises(SessionLostError) as excinfo:
        d.app_state()
    assert classify(excinfo.value) is Verdict.INFRA
    assert d.is_alive() is False


@pytest.mark.parametrize("case", WIRE_CONFORMANCE_CASES, ids=lambda c: c.__name__)
def test_wire_conformance_fake(case) -> None:
    case(FakeWireDriverHarness())


def _walk(node: FakeUiNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def _serve_one_shot_wire(port_box: list[int], ready: threading.Event) -> None:
    """Minimal NDJSON companion stand-in for TcpWireTransport integration."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port_box.append(srv.getsockname()[1])
    srv.listen(1)
    ready.set()
    conn, _ = srv.accept()
    with conn:
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                req = json.loads(line.decode("utf-8"))
                op = req.get("op")
                rid = req.get("id", "0")
                if op == "hello":
                    result = {
                        "protocol_version": PROTOCOL_VERSION,
                        "companion_version": "0.1.0",
                        "scene": "TcpFake",
                        "features": ["hooks", "ui"],
                    }
                elif op == "ping":
                    result = {"pong": True}
                elif op == "app_state":
                    result = {"foreground": True, "scene": "TcpFake", "paused": False}
                elif op == "hooks_manifest":
                    result = {
                        "hooks": [
                            {
                                "name": "Ping",
                                "args": [],
                                "causesSoftReload": False,
                                "feature": "smoke",
                            }
                        ]
                    }
                elif op == "call_hook":
                    result = {"value": "pong"}
                else:
                    resp = {
                        "v": 1,
                        "id": rid,
                        "ok": False,
                        "error": {"code": "authoring", "message": f"unknown {op}"},
                    }
                    conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
                    continue
                resp = {"v": 1, "id": rid, "ok": True, "result": result}
                conn.sendall((json.dumps(resp) + "\n").encode("utf-8"))
    srv.close()


def test_tcp_wire_transport_loopback() -> None:
    port_box: list[int] = []
    ready = threading.Event()
    t = threading.Thread(target=_serve_one_shot_wire, args=(port_box, ready), daemon=True)
    t.start()
    assert ready.wait(2.0)
    port = port_box[0]
    transport = connect_real_transport(ConnectionTarget(host="127.0.0.1", port=port))
    assert transport.request("ping") == {"pong": True}
    assert transport.request("app_state")["scene"] == "TcpFake"
    manifest = transport.request("hooks_manifest")
    assert manifest["hooks"][0]["name"] == "Ping"
    assert transport.request("call_hook", {"name": "Ping", "args": []}) == {"value": "pong"}
    transport.close()
    t.join(2.0)


def test_tcp_wire_driver_against_loopback() -> None:
    port_box: list[int] = []
    ready = threading.Event()
    t = threading.Thread(target=_serve_one_shot_wire, args=(port_box, ready), daemon=True)
    t.start()
    assert ready.wait(2.0)
    port = port_box[0]
    d = QuestlineDriver(rehandshake_delay_s=0.0, sleeper=lambda _s: None)
    d.connect(ConnectionTarget(host="127.0.0.1", port=port, platform="editor"))
    assert d.is_alive()
    assert d.call_game_method(GameHook(name="Ping")) == "pong"
    d.disconnect()
    t.join(2.0)


def test_default_tree_fixture() -> None:
    root = default_fake_ui_tree()
    assert root.id == "canvas"
    assert any(n.id == "btn_ok" for n in _walk(root))
