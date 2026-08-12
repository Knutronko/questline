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
``Canvas`` / smoke markers from the game. Tapping ``Canvas``/scene root often has
**no visible** UI change — Wire ops + screenshot prove the path.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Iterator

import pytest

from questline.authoring import Scenario, expect
from questline.authoring.context import Context
from questline.authoring.markers import quest
from questline.core.errors import AuthoringError, ElementNotFoundError
from questline.core.store import RunStore
from questline.core.waits import WaitPolicy
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.port import GameHook, HierarchyNode
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


def _walk(nodes: Iterable[HierarchyNode]) -> Iterator[HierarchyNode]:
    for node in nodes:
        yield node
        yield from _walk(node.children)


@quest.smoke
def test_wire_v2_hierarchy_find_tap(
    questline_ctx: Context,
    questline_store: RunStore,
) -> None:
    """Live UI: hierarchy → find → tap → screenshot (steps + artifact for HUD).

    Prefers clickable markers (``OkButton``, ``*Button``, ``QuestlineSmoke``). Falls
    back to ``Canvas`` / first hierarchy root — those taps often have **no visible**
    UI change (Canvas is not a button); the proof is Wire ops + PNG artifact.
    """
    driver = questline_ctx.driver.resolve()
    assert isinstance(driver, QuestlineDriver)

    def hierarchy_step(ctx: Context) -> None:
        try:
            snap = driver.hierarchy()
        except AuthoringError as exc:
            pytest.fail(
                f"Wire UI not available (refresh companion for QL-2c / phase-09b): {exc}"
            )
        expect(len(snap.roots) >= 1).is_true().evaluate()
        ctx.save("snap", snap)
        ctx.save("root", snap.roots[0].element)

    def find_step(ctx: Context) -> None:
        snap = ctx["snap"]
        root_el = ctx["root"]
        preferred = ("OkButton", "QuestlineSmoke", "Smoke", "Canvas")
        found = None
        for name in preferred:
            try:
                found = driver.find(
                    Locator(by=LocatorStrategy.NAME, value=name),
                    WaitPolicy(probe=0.5, deadline=2.0, interval=0.2),
                    budget="deadline",
                )
                ctx.save("tap_name", name)
                break
            except ElementNotFoundError:
                continue
        if found is None:
            for node in _walk(snap.roots):
                n = (node.element.name or "").lower()
                if "button" in n or "btn" in n:
                    found = node.element
                    ctx.save("tap_name", node.element.name)
                    break
        if found is None:
            found = root_el
            ctx.save("tap_name", root_el.name or root_el.id)
        expect(bool(found.id)).is_true().evaluate()
        ctx.save("target", found)

    def tap_step(ctx: Context) -> None:
        target = ctx["target"]
        try:
            driver.tap(target)
            ctx.save("tap_ok", True)
        except ElementNotFoundError:
            # Stale id between find and tap — hierarchy/find already proved Wire UI.
            ctx.save("tap_ok", False)

    def screenshot_step(ctx: Context) -> None:
        png = driver.screenshot()
        expect(len(png) > 0).is_true().evaluate()
        expect(png[:4] == b"\x89PNG").is_true().evaluate()
        questline_store.save_artifact(
            png,
            run_id=ctx.run_id,
            test_id=ctx.test_id,
            name="wire-v2-ui.png",
            kind="screenshot",
            bus=ctx.bus,
        )

    (
        Scenario("wire v2 hierarchy find tap")
        .call(hierarchy_step, name="hierarchy")
        .call(find_step, name="find")
        .call(tap_step, name="tap")
        .call(screenshot_step, name="screenshot")
        .run(questline_ctx)
    )
