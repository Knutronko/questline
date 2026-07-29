"""Page objects bound to a locator registry and DriverHandle (architecture §4)."""

from __future__ import annotations

from questline.authoring.context import Context
from questline.core.waits import WaitPolicy, resolve_policy
from questline.drivers.handle import DriverHandle
from questline.drivers.locators import Locator
from questline.drivers.port import Element


class Page:
    """Thin page: locators + DriverHandle; waits injected, never hardcoded."""

    def __init__(
        self,
        ctx: Context,
        *,
        wait: WaitPolicy | None = None,
    ) -> None:
        self._ctx = ctx
        self._page_wait = wait

    @property
    def ctx(self) -> Context:
        return self._ctx

    @property
    def driver(self) -> DriverHandle:
        """Live handle — never cache a raw DriverPort across session reset."""
        return self._ctx.driver

    def wait_policy(self, override: WaitPolicy | None = None) -> WaitPolicy:
        """Compose profile default < page override < call override."""
        base = resolve_policy(self._ctx.wait_policy, self._page_wait)
        return resolve_policy(base, override)

    def find(
        self,
        locator: Locator,
        policy: WaitPolicy | None = None,
        *,
        budget: str = "deadline",
    ) -> Element:
        return self.driver.find(locator, self.wait_policy(policy), budget=budget)

    def find_all(self, locator: Locator) -> list[Element]:
        return self.driver.find_all(locator)

    def tap(
        self,
        locator: Locator,
        policy: WaitPolicy | None = None,
        *,
        budget: str = "deadline",
    ) -> Element:
        element = self.find(locator, policy, budget=budget)
        self.driver.tap(element)
        return element

    def exists(self, locator: Locator, policy: WaitPolicy | None = None) -> bool:
        """Probe-budget presence check (does not raise on miss)."""
        from questline.core.errors import ElementNotFoundError

        try:
            self.find(locator, policy, budget="probe")
            return True
        except ElementNotFoundError:
            return False
