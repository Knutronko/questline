"""DriverHandle — live provider indirection so session reset never freezes a driver ref."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from questline.core.errors import InfraError
from questline.core.waits import WaitPolicy
from questline.drivers.locators import Locator
from questline.drivers.port import (
    AppState,
    ConnectionTarget,
    DriverPort,
    Element,
    GameHook,
    HierarchySnapshot,
    Point,
)


class DriverHandle:
    """All consumers hold this handle, never a raw DriverPort.

    ``reset()`` swaps the underlying driver atomically. Call sites that always go through
    the handle cannot observe a disposed driver after reset (stale-reference safe).
    """

    def __init__(
        self,
        driver: DriverPort | None = None,
        *,
        provider: Callable[[], DriverPort] | None = None,
    ) -> None:
        if driver is None and provider is None:
            raise InfraError("DriverHandle requires an initial driver or a provider")
        self._provider = provider
        self._driver = driver
        self._lock = threading.RLock()

    def resolve(self) -> DriverPort:
        """Return the live driver, creating one via provider if needed."""
        with self._lock:
            if self._driver is None:
                if self._provider is None:
                    raise InfraError("DriverHandle has no driver and no provider")
                self._driver = self._provider()
            return self._driver

    def reset(self, replacement: DriverPort | None = None) -> None:
        """Swap the underlying driver; dispose (disconnect) the previous one.

        If *replacement* is None and a provider was configured, the next ``resolve()``
        lazily creates a fresh driver. Consumers that only use handle methods keep working.
        """
        with self._lock:
            old = self._driver
            if replacement is not None:
                self._driver = replacement
            elif self._provider is not None:
                self._driver = None
            else:
                raise InfraError("reset() without replacement requires a provider")
        if old is not None:
            try:
                old.disconnect()
            except Exception:
                # Disposal must not block the swap; next call sites use the new driver.
                pass

    # --- DriverPort forwarders (always resolve live) ---

    def connect(self, target: ConnectionTarget) -> None:
        self.resolve().connect(target)

    def disconnect(self) -> None:
        self.resolve().disconnect()

    def is_alive(self) -> bool:
        return self.resolve().is_alive()

    def find(
        self,
        locator: Locator,
        policy: WaitPolicy | None = None,
        *,
        budget: str = "deadline",
    ) -> Element:
        return self.resolve().find(locator, policy, budget=budget)

    def find_all(self, locator: Locator) -> list[Element]:
        return self.resolve().find_all(locator)

    def hierarchy(self) -> HierarchySnapshot:
        return self.resolve().hierarchy()

    def screenshot(self) -> bytes:
        return self.resolve().screenshot()

    def tap(self, target: Element | Point) -> None:
        self.resolve().tap(target)

    def press(self, target: Element | Point, duration: float = 0.1) -> None:
        self.resolve().press(target, duration=duration)

    def swipe(
        self,
        start: Element | Point,
        end: Element | Point,
        duration: float = 0.2,
    ) -> None:
        self.resolve().swipe(start, end, duration=duration)

    def text_input(self, element: Element, text: str, *, clear: bool = True) -> None:
        self.resolve().text_input(element, text, clear=clear)

    def call_game_method(self, hook: GameHook, *args: Any) -> Any:
        return self.resolve().call_game_method(hook, *args)

    def app_state(self) -> AppState:
        return self.resolve().app_state()

    def compile(self, locator: Locator) -> Any:
        return self.resolve().compile(locator)
