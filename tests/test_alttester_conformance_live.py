"""Live AltTester conformance — skipped unless QUESTLINE_LIVE_TARGET=1.

Maintainer-checked against Editor play mode / standalone (see docs/unity-setup.md).
Pending game QL-1 until the reference game has AltTester + companion installed.
"""

from __future__ import annotations

import os

import pytest

from questline.drivers.alttester import AltTesterDriver
from questline.drivers.conformance import CONFORMANCE_CASES
from questline.drivers.port import ConnectionTarget

pytestmark = pytest.mark.requires_live_target


def _target_from_env() -> ConnectionTarget:
    platform = os.environ.get("QUESTLINE_LIVE_PLATFORM", "editor").strip() or "editor"
    host = os.environ.get("QUESTLINE_ALT_HOST", "127.0.0.1")
    port = int(os.environ.get("QUESTLINE_ALT_PORT", "13000"))
    app_name = os.environ.get("QUESTLINE_ALT_APP_NAME", "__default__")
    return ConnectionTarget(
        host=host,
        port=port,
        platform=platform,
        extras={"app_name": app_name},
    )


def _live_factory() -> AltTesterDriver:
    live = _target_from_env()
    driver = AltTesterDriver(rehandshake_delay_s=1.0)
    original_connect = driver.connect

    def connect_override(target: ConnectionTarget) -> None:
        merged = ConnectionTarget(
            host=live.host if target.host in {"127.0.0.1", ""} else target.host,
            port=live.port if target.port == 13000 else target.port,
            platform=live.platform or target.platform,
            app_id=live.app_id or target.app_id,
            extras={**live.extras, **dict(target.extras)},
        )
        original_connect(merged)

    driver.connect = connect_override  # type: ignore[method-assign]
    return driver


@pytest.mark.parametrize("case", CONFORMANCE_CASES, ids=lambda c: c.__name__)
def test_alttester_live_conformance(case) -> None:
    """Live half of conformance (Editor / standalone).

    Cases that need mock-only hooks (schedule_appear / drop_after) skip when absent.
    Game fixture must expose elements the seed expects, or find-hit cases may fail —
    see docs/unity-setup.md smoke locators.
    """
    case(_live_factory)
