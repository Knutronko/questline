"""Unit + fake-transport tests for QuestlineWire (CI-green, no Unity)."""

from __future__ import annotations

import json
import socket
import threading
from typing import Any

import pytest

from questline.core.errors import (
    AuthoringError,
    InfraError,
    SessionLostError,
    TestError,
    Verdict,
    classify,
)
from questline.drivers.conformance import WIRE_CONFORMANCE_CASES
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.port import ConnectionTarget, Element, GameHook, Point
from questline.drivers.wire import QuestlineDriver
from questline.drivers.wire.errors import error_from_server, map_wire_error, mvp_ui_not_implemented
from questline.drivers.wire.fake import FakeWireDriverHarness, fake_transport_factory
from questline.drivers.wire.protocol import make_request, parse_response
from questline.drivers.wire.transport import connect_real_transport


def test_protocol_roundtrip() -> None:
    line = make_request("ping", req_id="abc")
    assert '"op":"ping"' in line
    assert '"id":"abc"' in line
    data = parse_response('{"v":1,"id":"abc","ok":true,"result":{"pong":true}}')
    assert data["ok"] is True


def test_error_mapping() -> None:
    assert isinstance(error_from_server("authoring", "bad"), AuthoringError)
    assert isinstance(error_from_server("test", "boom"), TestError)
    assert isinstance(error_from_server("session_lost", "gone"), SessionLostError)
    assert classify(map_wire_error(ConnectionRefusedError("x"))) is Verdict.INFRA
    assert "Wire MVP" in str(mvp_ui_not_implemented())


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


def test_ui_methods_authoring_error() -> None:
    harness = FakeWireDriverHarness()
    d = harness()
    d.connect(ConnectionTarget())
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.hierarchy()
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.screenshot()
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.find_all(Locator(by=LocatorStrategy.ID, value="x"))
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.tap(Point(0, 0))
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.press(Point(0, 0))
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.swipe(Point(0, 0), Point(1, 1))
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.text_input(
            Element(id="x"),
            "hi",
        )
    with pytest.raises(AuthoringError, match="Wire MVP"):
        d.compile(Locator(by=LocatorStrategy.ID, value="x"))
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
                        "protocol_version": 1,
                        "companion_version": "0.1.0",
                        "scene": "TcpFake",
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

