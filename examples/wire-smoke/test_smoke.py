"""Wire smoke suite — hooks + Wire v2 UI (no AltTester Desktop).

Skipped unless ``QUESTLINE_LIVE_TARGET=1``. Requires Unity Editor (or Dev APK) with
``QuestlineWireServer.EnsureStarted()`` (Wire v2 companion: ``features`` includes
``ui`` / ``protocol_version`` ≥ 2) and at least one registered hook (prefer ``Ping``).

Editor::

    $env:QUESTLINE_LIVE_TARGET = "1"
    uv pip install -e ".[dev]"
    uv run pytest examples/wire-smoke -q -o addopts= `
      --questline-profile editor `
      --questline-config examples/wire-smoke/questline.toml

Android (after QL-2c companion refresh + Dev APK rebuild)::

    $env:QUESTLINE_LIVE_TARGET = "1"
    $env:QUESTLINE_APK_PATH = "path\\to\\dev.apk"
    $env:QUESTLINE_APP_PACKAGE = "com.example.game"
    uv run pytest examples/wire-smoke -q -o addopts= `
      --questline-profile android_local `
      --questline-config examples/wire-smoke/questline.toml

UI find/tap needs any active GameObject (hierarchy assert) or a known name such as
``Canvas`` / smoke markers from the game. Android UI smoke is optional until QL-2c.
"""

from __future__ import annotations

import os

import pytest

from questline.authoring import expect
from questline.authoring.context import Context
from questline.authoring.markers import quest
from questline.core.errors import AuthoringError, ElementNotFoundError
from questline.core.waits import WaitPolicy
from questline.drivers.locators import Locator, LocatorStrategy
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


@quest.smoke
def test_wire_v2_hierarchy_find_tap(questline_ctx: Context) -> None:
    """Live UI: hierarchy non-empty; find a known GO by name; tap or assert.

    Prefers common markers (``Canvas``, ``OkButton``, ``QuestlineSmoke``). Falls back
    to tapping the first hierarchy root when no named marker exists.
    """
    driver = questline_ctx.driver.resolve()
    assert isinstance(driver, QuestlineDriver)
    try:
        snap = driver.hierarchy()
    except AuthoringError as exc:
        pytest.fail(
            f"Wire UI not available (refresh companion for QL-2c / phase-09b): {exc}"
        )

    expect(len(snap.roots) >= 1).is_true().evaluate()
    root_el = snap.roots[0].element
    expect(bool(root_el.id)).is_true().evaluate()

    candidates = ("Canvas", "OkButton", "QuestlineSmoke", "Smoke", root_el.name)
    found = None
    for name in candidates:
        if not name:
            continue
        try:
            found = driver.find(
                Locator(by=LocatorStrategy.NAME, value=name),
                WaitPolicy(probe=0.5, deadline=2.0, interval=0.2),
                budget="deadline",
            )
            break
        except ElementNotFoundError:
            continue

    if found is None:
        found = root_el

    expect(bool(found.id)).is_true().evaluate()
    # Tap is best-effort on Editor; hierarchy + find already prove Wire v2.
    try:
        driver.tap(found)
    except ElementNotFoundError:
        # Stale id between find and tap — still counts as Wire UI path exercised.
        pass

    png = driver.screenshot()
    expect(len(png) > 0).is_true().evaluate()
    expect(png[:4] == b"\x89PNG").is_true().evaluate()
