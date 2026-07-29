"""Demo page objects over generated locators."""

from __future__ import annotations

import sys
from pathlib import Path

from questline.authoring.context import Context
from questline.authoring.pages import Page
from questline.core.waits import WaitPolicy

_EXAMPLES = Path(__file__).resolve().parents[1]
if str(_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES))

from generated_locators import Hud, MainMenu, Popup, Shop  # noqa: E402


class MainMenuPage(Page):
    def __init__(self, ctx: Context, *, wait: WaitPolicy | None = None) -> None:
        super().__init__(ctx, wait=wait)

    def play(self) -> None:
        self.tap(MainMenu.play_button)


class HudPage(Page):
    def coins_text(self) -> str:
        return self.find(Hud.coins_label).text

    def open_shop(self) -> None:
        self.tap(Hud.shop_button)


class ShopPage(Page):
    def wait_open(self) -> None:
        self.find(Shop.root)

    def buy_pack(self) -> None:
        self.tap(Shop.buy_pack_button)

    def close(self) -> None:
        self.tap(Shop.close_button)


class PopupPage(Page):
    rate_us = Popup.rate_us
    dismiss = Popup.dismiss
