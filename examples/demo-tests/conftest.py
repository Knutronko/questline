"""Demo suite conftest — wire MockDriver scene into the session DriverHandle."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from questline.drivers.mock import MockDriver
from questline.drivers.port import ConnectionTarget

_EXAMPLES = Path(__file__).resolve().parents[1]
if str(_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES))

from scene import build_demo_scene  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_demo_scene(driver_handle, request: pytest.FixtureRequest):
    """Fresh demo scene per test; popup variant via marker ``demo_popup``."""
    with_popup = request.node.get_closest_marker("demo_popup") is not None
    scene = build_demo_scene(with_rate_popup=with_popup)
    driver = MockDriver(scene)
    driver.connect(ConnectionTarget(host="mock", port=0))
    driver_handle.reset(driver)
    return scene


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "demo_popup: enable RateUs popup in the demo scene")


@pytest.fixture
def demo_root() -> Path:
    return Path(__file__).resolve().parent
