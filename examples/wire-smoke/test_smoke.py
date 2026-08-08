"""Wire smoke suite — hooks-first live path (no AltTester Desktop).

Skipped unless ``QUESTLINE_LIVE_TARGET=1``. Requires Unity Editor (or Dev APK) with
``QuestlineWireServer.EnsureStarted()`` and at least one registered hook (prefer ``Ping``).

Editor::

    $env:QUESTLINE_LIVE_TARGET = "1"
    uv pip install -e ".[dev]"
    uv run pytest examples/wire-smoke -q -o addopts= `
      --questline-profile editor `
      --questline-config examples/wire-smoke/questline.toml

Android (after QL-2b Wire bootstrap + Dev APK)::

    $env:QUESTLINE_LIVE_TARGET = "1"
    $env:QUESTLINE_APK_PATH = "path\\to\\dev.apk"
    $env:QUESTLINE_APP_PACKAGE = "com.example.game"
    uv run pytest examples/wire-smoke -q -o addopts= `
      --questline-profile android_local `
      --questline-config examples/wire-smoke/questline.toml
"""

from __future__ import annotations

import os

import pytest

from questline.authoring import expect
from questline.authoring.context import Context
from questline.authoring.markers import quest
from questline.drivers.port import GameHook
from questline.drivers.wire import QuestlineDriver

pytestmark = pytest.mark.requires_live_target


@pytest.fixture(autouse=True)
def _require_live() -> None:
    if os.environ.get("QUESTLINE_LIVE_TARGET", "").strip() != "1":
        pytest.skip(
            "set QUESTLINE_LIVE_TARGET=1 with Unity QuestlineWire + companion hooks running"
        )


@quest.smoke
def test_app_boots(questline_ctx: Context) -> None:
    state = questline_ctx.driver.app_state()
    expect(state.foreground).is_true().evaluate()
    expect(bool(state.scene)).is_true().evaluate()


@quest.smoke
def test_hooks_manifest_and_ping(questline_ctx: Context) -> None:
    driver = questline_ctx.driver.resolve()
    assert isinstance(driver, QuestlineDriver)
    manifest = driver.hooks_manifest()
    expect(isinstance(manifest, list)).is_true().evaluate()
    expect(len(manifest) >= 1).is_true().evaluate()
    names = {e.name for e in manifest}
    if "Ping" in names:
        result = questline_ctx.driver.call_game_method(GameHook(name="Ping"))
        expect(result).equals("pong").evaluate()
    else:
        entry = next(e for e in manifest if len(e.args) == 0)
        questline_ctx.driver.call_game_method(
            GameHook(name=entry.name, causes_soft_reload=entry.causes_soft_reload)
        )


@quest.smoke
def test_driver_is_questline_wire(questline_ctx: Context) -> None:
    driver = questline_ctx.driver.resolve()
    expect(isinstance(driver, QuestlineDriver)).is_true().evaluate()
    expect(driver.is_alive()).is_true().evaluate()
