"""Locator → AltTester native query compilation."""

from __future__ import annotations

from dataclasses import dataclass

from questline.core.errors import AuthoringError
from questline.drivers.locators import Locator, LocatorStrategy


@dataclass(frozen=True, slots=True)
class AltNativeQuery:
    """Compiled AltTester selector (By enum name + value)."""

    by: str
    value: str
    scope: str | None = None


_STRATEGY_TO_BY: dict[LocatorStrategy, str] = {
    LocatorStrategy.ID: "ID",
    LocatorStrategy.NAME: "NAME",
    LocatorStrategy.PATH: "PATH",
    LocatorStrategy.TEXT: "TEXT",
    LocatorStrategy.COMPONENT: "COMPONENT",
}


def compile_locator(locator: Locator) -> AltNativeQuery:
    """Compile a driver-agnostic Locator into an AltTester query."""
    by = _STRATEGY_TO_BY.get(locator.by)
    if by is None:
        raise AuthoringError(f"unsupported locator strategy for AltTester: {locator.by!r}")
    return AltNativeQuery(by=by, value=locator.value, scope=locator.scope)
