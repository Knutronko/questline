"""Fake mini-game scene for the phase-03 demo suite (MockDriver)."""

from __future__ import annotations

from questline.drivers.mock.scene import MockNode, MockScene


def build_demo_scene(*, with_rate_popup: bool = False) -> MockScene:
    """Build a MainMenu → Hud → Shop flow; optional RateUs popup."""
    scene = MockScene()
    scene.scene_name = "DemoGame"

    state = {"coins": 100, "screen": "main", "packs": 0}

    main = MockNode(id="main.root", name="MainMenu", path="/MainMenu")
    play = MockNode(id="main.play", name="PlayButton", path="/MainMenu/Play", text="Play")
    scene.add(main)
    scene.add(play, parent=main)

    hud = MockNode(id="hud.root", name="Hud", path="/Hud", visible=False)
    coins = MockNode(
        id="hud.coins",
        name="CoinsLabel",
        path="/Hud/Coins",
        text=_coins_text(state["coins"]),
        visible=False,
    )
    shop_btn = MockNode(
        id="hud.shop",
        name="ShopButton",
        path="/Hud/ShopBtn",
        text="Shop",
        visible=False,
    )
    scene.add(hud)
    scene.add(coins, parent=hud)
    scene.add(shop_btn, parent=hud)

    shop = MockNode(id="shop.root", name="ShopPanel", path="/Shop", visible=False)
    buy = MockNode(
        id="shop.buy_pack",
        name="BuyPack",
        path="/Shop/Buy",
        text="Buy Pack",
        visible=False,
    )
    close = MockNode(
        id="shop.close",
        name="CloseShop",
        path="/Shop/Close",
        text="Close",
        visible=False,
    )
    scene.add(shop)
    scene.add(buy, parent=shop)
    scene.add(close, parent=shop)

    popup = MockNode(id="popup.rate_us", name="RateUs", path="/Popup/RateUs", visible=False)
    dismiss = MockNode(
        id="popup.dismiss",
        name="Dismiss",
        path="/Popup/Dismiss",
        text="Later",
        visible=False,
    )
    scene.add(popup)
    scene.add(dismiss, parent=popup)

    def _show_hud() -> None:
        state["screen"] = "hud"
        main.visible = False
        play.visible = False
        hud.visible = True
        coins.visible = True
        shop_btn.visible = True
        shop.visible = False
        buy.visible = False
        close.visible = False
        if with_rate_popup:
            popup.visible = True
            dismiss.visible = True

    def _show_shop() -> None:
        state["screen"] = "shop"
        shop.visible = True
        buy.visible = True
        close.visible = True

    def _hide_shop() -> None:
        state["screen"] = "hud"
        shop.visible = False
        buy.visible = False
        close.visible = False

    def _buy_pack() -> None:
        state["coins"] -= 50
        state["packs"] += 1
        coins.text = _coins_text(state["coins"])

    def _dismiss_popup() -> None:
        popup.visible = False
        dismiss.visible = False

    play.on_tap = _show_hud
    shop_btn.on_tap = _show_shop
    close.on_tap = _hide_shop
    buy.on_tap = _buy_pack
    dismiss.on_tap = _dismiss_popup
    popup.on_tap = _dismiss_popup

    scene.hooks["GetCoins"] = lambda: state["coins"]
    scene.hooks["GetPacks"] = lambda: state["packs"]

    def _grant(n: object) -> int:
        state["coins"] = state["coins"] + int(n)  # type: ignore[arg-type]
        coins.text = _coins_text(state["coins"])
        return state["coins"]

    scene.hooks["GrantCoins"] = _grant
    scene._demo_state = state  # type: ignore[attr-defined]
    return scene


def _coins_text(n: int) -> str:
    return f"Coins: {n}"
