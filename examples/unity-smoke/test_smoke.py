"""Unity smoke suite — requires a live AltTester target + companion package.

Skipped unless ``QUESTLINE_LIVE_TARGET=1``. Editor/standalone: game QL-1. Android:
``--questline-profile android_local`` (needs instrumented APK — **pending game QL-2**
or a sample-project APK; see ``docs/android.md``).

Run (Editor play mode with AltTester listening on :13000)::

    set QUESTLINE_LIVE_TARGET=1
    uv pip install -e ".[dev,alttester]"
    uv run pytest examples/unity-smoke -q -o addopts= \
      --questline-profile editor \
      --questline-config examples/unity-smoke/questline.toml

Android (device/emulator + adb reverse)::

    set QUESTLINE_LIVE_TARGET=1
    set QUESTLINE_APK_PATH=path\to\dev.apk
    set QUESTLINE_APP_PACKAGE=com.example.game
    uv run pytest examples/unity-smoke -q -o addopts= \
      --questline-profile android_local \
      --questline-config examples/unity-smoke/questline.toml
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from generated_locators import Smoke

from questline.authoring import Scenario, Tap, WaitFor, expect
from questline.authoring.context import Context
from questline.authoring.markers import quest
from questline.drivers.alttester import AltTesterDriver
from questline.drivers.port import GameHook

pytestmark = pytest.mark.requires_live_target

_ARTIFACTS = Path(__file__).resolve().parent / ".artifacts"


@pytest.fixture(autouse=True)
def _require_live() -> None:
    if os.environ.get("QUESTLINE_LIVE_TARGET", "").strip() != "1":
        pytest.skip("set QUESTLINE_LIVE_TARGET=1 with Unity AltTester + companion running")


@quest.smoke
def test_app_boots(questline_ctx: Context) -> None:
    state = questline_ctx.driver.app_state()
    expect(state.foreground).is_true().evaluate()
    expect(bool(state.scene)).is_true().evaluate()


@quest.smoke
def test_hierarchy_non_empty(questline_ctx: Context) -> None:
    snap = questline_ctx.driver.hierarchy()
    expect(len(snap.roots) > 0).is_true().evaluate()


@quest.smoke
def test_tap_smoke_button(questline_ctx: Context) -> None:
    scenario = (
        Scenario("tap smoke button")
        .step(WaitFor(Smoke.root))
        .step(Tap(Smoke.button))
    )
    scenario.run(questline_ctx)


@quest.smoke
def test_call_hook_and_manifest(questline_ctx: Context) -> None:
    """Addendum: single driver call returns the hooks registry dump."""
    driver = questline_ctx.driver.resolve()
    assert isinstance(driver, AltTesterDriver)
    manifest = driver.hooks_manifest()
    expect(isinstance(manifest, list)).is_true().evaluate()
    # Game should register at least one hook for smoke (e.g. Ping or SkipTutorial).
    expect(len(manifest) >= 1).is_true().evaluate()
    names = {e.name for e in manifest}
    # Prefer Ping if present; otherwise call the first registered hook with no required args.
    if "Ping" in names:
        result = questline_ctx.driver.call_game_method(GameHook(name="Ping"))
        expect(result).equals("pong").evaluate()
    else:
        entry = next(e for e in manifest if len(e.args) == 0)
        questline_ctx.driver.call_game_method(
            GameHook(name=entry.name, causes_soft_reload=entry.causes_soft_reload)
        )


@quest.smoke
def test_screenshot_artifact_saved(questline_ctx: Context) -> None:
    _ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = _ARTIFACTS / "smoke-screenshot.png"
    data = questline_ctx.driver.screenshot()
    expect(len(data) > 0).is_true().evaluate()
    path.write_bytes(data)
    expect(path.is_file()).is_true().evaluate()
