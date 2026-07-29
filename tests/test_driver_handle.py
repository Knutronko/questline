"""DriverHandle stale-reference and reset semantics."""

from __future__ import annotations

import pytest

from questline.core.errors import InfraError, SessionLostError
from questline.drivers.handle import DriverHandle
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget


def _driver_with_button(label: str) -> MockDriver:
    scene = MockScene()
    scene.add(MockNode(id="btn", name=label, text=label))
    d = MockDriver(scene)
    d.connect(ConnectionTarget())
    return d


def test_handle_reset_swaps_driver_consumers_keep_working() -> None:
    """Old driver is disposed; handle callers keep working on the replacement."""
    first = _driver_with_button("first")
    second = _driver_with_button("second")
    handle = DriverHandle(first)

    el1 = handle.find(Locator(by=LocatorStrategy.ID, value="btn"))
    assert el1.name == "first"

    handle.reset(second)

    # Stale raw reference is dead — using it must fail.
    with pytest.raises(SessionLostError):
        first.find(Locator(by=LocatorStrategy.ID, value="btn"))
    assert first.is_alive() is False

    # Consumers that only hold the handle see the live driver.
    el2 = handle.find(Locator(by=LocatorStrategy.ID, value="btn"))
    assert el2.name == "second"
    assert handle.is_alive() is True

    handle.disconnect()


def test_handle_reset_with_provider_lazily_recreates() -> None:
    created: list[MockDriver] = []

    def provider() -> MockDriver:
        d = _driver_with_button(f"gen-{len(created)}")
        created.append(d)
        return d

    handle = DriverHandle(provider=provider)
    assert handle.find(Locator(by=LocatorStrategy.ID, value="btn")).name == "gen-0"
    handle.reset()
    assert handle.find(Locator(by=LocatorStrategy.ID, value="btn")).name == "gen-1"
    assert created[0].is_alive() is False
    handle.disconnect()


def test_handle_requires_driver_or_provider() -> None:
    with pytest.raises(InfraError):
        DriverHandle()
