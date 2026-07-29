"""Demo e2e tests against MockDriver (phase-03 authoring layer)."""

from __future__ import annotations

import pytest
from generated_locators import Hud, MainMenu, Popup, Shop
from pages import HudPage, MainMenuPage, ShopPage

from questline.authoring import (
    AssertThat,
    HandleOptional,
    Save,
    Scenario,
    Tap,
    WaitFor,
    expect,
)
from questline.authoring.context import Context
from questline.authoring.markers import quest
from questline.drivers.port import GameHook


@quest.smoke
@pytest.mark.feature("demo-main-menu")
def test_play_reaches_hud(questline_ctx: Context) -> None:
    MainMenuPage(questline_ctx).play()
    questline_ctx.driver.find(Hud.root, questline_ctx.wait_policy)
    text = HudPage(questline_ctx).coins_text()
    expect(text).equals("Coins: 100").evaluate()


@quest.smoke
@pytest.mark.feature("demo-shop")
def test_open_shop_via_scenario(questline_ctx: Context) -> None:
    scenario = (
        Scenario("open shop")
        .step(Tap(MainMenu.play_button))
        .step(WaitFor(Hud.root))
        .step(Tap(Hud.shop_button))
        .step(WaitFor(Shop.root))
        .step(
            AssertThat(
                lambda ctx: expect(ctx.driver.find(Shop.buy_pack_button).text).equals(
                    "Buy Pack"
                )
            )
        )
    )
    scenario.run(questline_ctx)


@quest.regression
@pytest.mark.feature("demo-shop")
def test_buy_pack_updates_coins(questline_ctx: Context) -> None:
    MainMenuPage(questline_ctx).play()
    hud = HudPage(questline_ctx)
    shop = ShopPage(questline_ctx)
    hud.open_shop()
    shop.wait_open()
    shop.buy_pack()
    shop.close()
    expect(hud.coins_text()).equals("Coins: 50").evaluate()
    packs = questline_ctx.driver.call_game_method(GameHook(name="GetPacks"))
    expect(packs).equals(1).evaluate()


@quest.regression
@pytest.mark.feature("demo-shop")
def test_scenario_save_data_flow(questline_ctx: Context) -> None:
    scenario = (
        Scenario("buy with save")
        .step(Tap(MainMenu.play_button))
        .step(WaitFor(Hud.root))
        .step(
            Save(
                "coins_before",
                lambda ctx: ctx.driver.call_game_method(GameHook(name="GetCoins")),
            )
        )
        .step(Tap(Hud.shop_button))
        .step(WaitFor(Shop.root))
        .step(Tap(Shop.buy_pack_button))
        .call(
            lambda ctx: ctx.save(
                "coins_after",
                ctx.driver.call_game_method(GameHook(name="GetCoins")),
            )
        )
        .step(
            AssertThat(
                lambda ctx: expect(ctx["coins_after"]).equals(ctx["coins_before"] - 50)
            )
        )
    )
    scenario.run(questline_ctx)
    expect(questline_ctx["coins_after"]).equals(50).evaluate()


@pytest.mark.demo_popup
@quest.smoke
@pytest.mark.feature("demo-popup")
def test_optional_rate_popup_dismissed(questline_ctx: Context) -> None:
    scenario = (
        Scenario("dismiss popup")
        .step(Tap(MainMenu.play_button))
        .step(WaitFor(Hud.root))
        .step(
            HandleOptional(
                Popup.rate_us,
                Tap(Popup.dismiss, budget="probe"),
            )
        )
        .step(Tap(Hud.shop_button))
        .step(WaitFor(Shop.root))
    )
    scenario.run(questline_ctx)


@quest.smoke
@pytest.mark.feature("demo-popup")
def test_optional_popup_absent_is_noop(questline_ctx: Context) -> None:
    """Without demo_popup marker the RateUs node stays hidden — probe moves on."""
    scenario = (
        Scenario("no popup")
        .step(Tap(MainMenu.play_button))
        .step(WaitFor(Hud.root))
        .step(HandleOptional(Popup.rate_us))
        .step(Tap(Hud.shop_button))
        .step(WaitFor(Shop.root))
    )
    scenario.run(questline_ctx)


@quest.regression
@pytest.mark.feature("demo-shop")
def test_page_wait_policy_override(questline_ctx: Context) -> None:
    from questline.core.waits import WaitPolicy

    page = MainMenuPage(
        questline_ctx, wait=WaitPolicy(probe=0.1, deadline=1.0, interval=0.05)
    )
    page.play()
    HudPage(questline_ctx).coins_text()


@quest.quarantined
@pytest.mark.feature("demo-shop")
def test_flaky_buy_quarantined(questline_ctx: Context) -> None:
    """Ledger-backed quarantine demo — excluded unless --include-quarantined."""
    MainMenuPage(questline_ctx).play()
    HudPage(questline_ctx).open_shop()
    ShopPage(questline_ctx).buy_pack()
