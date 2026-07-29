"""Extra coverage for handle forwarders, locator edge cases, mock queries."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.errors import AuthoringError, ElementNotFoundError, InfraError
from questline.drivers.codegen import _ident, generate_module
from questline.drivers.handle import DriverHandle
from questline.drivers.locators import Locator, LocatorRegistry, LocatorStrategy, load_locators
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget, GameHook, Point


class _BoomDisconnect(MockDriver):
    def disconnect(self) -> None:
        raise RuntimeError("disconnect failed")


def test_handle_forwards_all_port_methods() -> None:
    scene = MockScene()
    root = MockNode(id="root", name="Root", path="/Root")
    btn = MockNode(id="btn", name="Btn", text="hi", path="/Root/Btn", component="Button")
    scene.add(root)
    scene.add(btn, parent=root)
    scene.hooks["Ping"] = lambda: "pong"
    driver = MockDriver(scene)
    handle = DriverHandle(driver)
    handle.connect(ConnectionTarget(port=1))
    assert handle.is_alive()
    loc = Locator(by=LocatorStrategy.ID, value="btn")
    assert handle.find(loc).id == "btn"
    assert handle.find_all(loc)
    assert handle.hierarchy().roots
    assert handle.screenshot()
    handle.tap(handle.find(loc))
    handle.press(Point(1, 2), duration=0.01)
    handle.swipe(Point(0, 0), Point(1, 1))
    handle.text_input(handle.find(loc), "x", clear=False)
    assert handle.call_game_method(GameHook("Ping")) == "pong"
    assert handle.app_state().foreground is True
    assert handle.compile(loc).value == "btn"
    handle.disconnect()


def test_handle_reset_swallows_disconnect_errors() -> None:
    boom = _BoomDisconnect(MockScene())
    boom.connect(ConnectionTarget())
    nxt = MockDriver(MockScene())
    nxt.connect(ConnectionTarget())
    handle = DriverHandle(boom)
    handle.reset(nxt)  # must not raise despite boom.disconnect failing
    assert handle.is_alive() is True


def test_handle_reset_without_provider_requires_replacement() -> None:
    handle = DriverHandle(MockDriver())
    with pytest.raises(InfraError, match="provider"):
        handle.reset()


def test_locator_registry_errors(tmp_path: Path) -> None:
    with pytest.raises(AuthoringError, match="mapping of pages"):
        LocatorRegistry.from_mapping({"pages": "nope"})
    with pytest.raises(AuthoringError, match="locator names"):
        LocatorRegistry.from_mapping({"pages": {"A": "nope"}})
    reg = load_locators(Path(__file__).resolve().parents[1] / "examples" / "locators.yaml")
    with pytest.raises(AuthoringError, match="unknown locator"):
        reg.get("Nope", "x")
    with pytest.raises(AuthoringError, match="unknown page"):
        reg.locators_for("Nope")
    assert reg.all_entries()
    assert Locator(by="id", value="x").by is LocatorStrategy.ID  # type: ignore[arg-type]

    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    assert load_locators(empty).pages() == []

    bad_root = tmp_path / "list.yaml"
    bad_root.write_text("- a\n", encoding="utf-8")
    with pytest.raises(AuthoringError, match="mapping"):
        load_locators(bad_root)

    bad_spec = tmp_path / "spec.yaml"
    bad_spec.write_text("pages:\n  A:\n    b: just-a-string\n", encoding="utf-8")
    with pytest.raises(AuthoringError, match="mapping"):
        load_locators(bad_spec)

    missing = tmp_path / "miss.yaml"
    missing.write_text("pages:\n  A:\n    b:\n      by: id\n", encoding="utf-8")
    with pytest.raises(AuthoringError, match="by' and 'value"):
        load_locators(missing)

    broken = tmp_path / "broken.yaml"
    broken.write_text("pages: [\n", encoding="utf-8")
    with pytest.raises(AuthoringError, match="invalid YAML"):
        load_locators(broken)


def test_codegen_ident_edge_cases() -> None:
    assert _ident("") == "unnamed"
    assert _ident("1abc") == "_1abc"
    assert _ident("a-b") == "a_b"


def test_mock_query_strategies_and_errors() -> None:
    scene = MockScene()
    parent = MockNode(id="canvas", name="Canvas", path="/Canvas")
    child = MockNode(
        id="n1",
        name="Child",
        text="Hello",
        path="/Canvas/Child",
        component="Comp",
        enabled=False,
    )
    scene.add(parent)
    scene.add(child, parent=parent)
    d = MockDriver(scene)
    d.connect(ConnectionTarget())
    d.set_screenshot(b"abc")
    assert d.screenshot() == b"abc"

    assert d.find(Locator(by=LocatorStrategy.PATH, value="/Canvas/Child")).id == "n1"
    assert d.find(Locator(by=LocatorStrategy.TEXT, value="Hello")).id == "n1"
    assert d.find(Locator(by=LocatorStrategy.COMPONENT, value="Comp")).id == "n1"
    assert d.find(
        Locator(by=LocatorStrategy.NAME, value="Child", scope="Canvas")
    ).id == "n1"

    with pytest.raises(ElementNotFoundError, match="disabled"):
        d.tap(child.to_element(now=0.0))
    with pytest.raises(ElementNotFoundError, match="not found"):
        d.tap(child.to_element(now=0.0).__class__(id="missing"))
    with pytest.raises(AuthoringError):
        d.schedule_appear("missing", 0.1)
    with pytest.raises(AuthoringError):
        d.drop_after_commands(0)
    with pytest.raises(AuthoringError):
        d.call_game_method(GameHook("Nope"))
    with pytest.raises(AuthoringError):
        d.find(Locator(by=LocatorStrategy.ID, value="n1"), budget="nope")  # type: ignore[arg-type]

    d.force_disconnect()
    assert d.is_alive() is False
    d.disconnect()


def test_mock_disposed_reconnect_fails() -> None:
    d = MockDriver()
    d.connect(ConnectionTarget())
    d.disconnect()
    with pytest.raises(Exception, match="disposed"):
        d.connect(ConnectionTarget())


def test_generate_module_with_scoped_locator() -> None:
    reg = LocatorRegistry.from_mapping(
        {
            "pages": {
                "P": {"x": {"by": "id", "value": "1", "scope": "root"}},
            }
        }
    )
    src = generate_module(reg, source="s.yaml", output="o.py")
    assert "scope='root'" in src or 'scope="root"' in src
