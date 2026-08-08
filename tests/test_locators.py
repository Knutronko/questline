"""Locator model, YAML registry, and codegen."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from questline.core.errors import AuthoringError
from questline.drivers.codegen import generate_module, write_generated
from questline.drivers.codegen import main as codegen_main
from questline.drivers.locators import Locator, LocatorStrategy, load_locators
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
LOCATORS_YAML = EXAMPLES / "locators.yaml"


def test_load_sample_locators_yaml() -> None:
    registry = load_locators(LOCATORS_YAML)
    assert "Shop" in registry.pages()
    loc = registry.get("Shop", "open_button")
    assert loc.by is LocatorStrategy.ID
    assert loc.value == "hud.shop"
    scoped = registry.get("Shop", "root")
    assert scoped.scope is None
    assert scoped.value == "shop.root"


def test_codegen_roundtrip_and_generated_module_used(tmp_path: Path) -> None:
    registry = load_locators(LOCATORS_YAML)
    out = tmp_path / "generated_locators.py"
    write_generated(registry, out, source=str(LOCATORS_YAML))
    text = out.read_text(encoding="utf-8")
    assert "DO NOT EDIT BY HAND" in text
    assert "class Shop:" in text
    assert "open_button" in text

    # Committed generated module is importable and usable against MockDriver.
    sys.path.insert(0, str(EXAMPLES))
    try:
        import generated_locators as gen  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)

    scene = MockScene()
    scene.add(MockNode(id="hud.shop", name="ShopButton", path="/Hud/Shop"))
    driver = MockDriver(scene)
    driver.connect(ConnectionTarget())
    el = driver.find(gen.Shop.open_button)
    assert el.id == "hud.shop"
    compiled = driver.compile(gen.Shop.root)
    assert compiled.value == "shop.root"
    driver.disconnect()


def test_codegen_cli(tmp_path: Path) -> None:
    out = tmp_path / "out.py"
    assert codegen_main([str(LOCATORS_YAML), "-o", str(out)]) == 0
    assert out.is_file()
    assert "LocatorStrategy" in out.read_text(encoding="utf-8")


def test_generate_module_empty_page() -> None:
    from questline.drivers.locators import LocatorRegistry

    reg = LocatorRegistry.from_mapping({"pages": {"Empty": {}}})
    src = generate_module(reg, source="x.yaml", output="y.py")
    assert "class Empty:" in src
    assert "pass" in src


def test_locator_rejects_empty_value() -> None:
    with pytest.raises(AuthoringError):
        Locator(by=LocatorStrategy.ID, value="")


def test_load_locators_missing_file(tmp_path: Path) -> None:
    with pytest.raises(AuthoringError, match="not found"):
        load_locators(tmp_path / "nope.yaml")


def test_load_locators_bad_strategy(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("pages:\n  A:\n    b:\n      by: nope\n      value: x\n", encoding="utf-8")
    with pytest.raises(AuthoringError, match="unknown strategy"):
        load_locators(p)
