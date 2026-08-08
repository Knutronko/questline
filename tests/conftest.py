"""Shared pytest fixtures for the unit suite."""

from __future__ import annotations

import os

import pytest

# Enable pytester for in-process plugin tests (not enabled by default).
pytest_plugins = ["pytester"]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_live_target: needs a running Unity AltTester session "
        "(set QUESTLINE_LIVE_TARGET=1)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    _ = config
    if os.environ.get("QUESTLINE_LIVE_TARGET", "").strip() == "1":
        return
    skip = pytest.mark.skip(
        reason="requires live Unity target (set QUESTLINE_LIVE_TARGET=1)"
    )
    for item in items:
        if item.get_closest_marker("requires_live_target") is not None:
            item.add_marker(skip)
