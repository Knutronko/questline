"""Authoring layer: pytest plugin, pages, steps, assertions, quarantine.

Keep this package init light so the pytest entry point does not import the whole
tree before pytest-cov starts measuring. Public names resolve via ``__getattr__``.
"""

from __future__ import annotations

__all__ = [
    "AssertThat",
    "Context",
    "Expectation",
    "HandleOptional",
    "Page",
    "QuarantineEntry",
    "QuarantineLedger",
    "Save",
    "Scenario",
    "Step",
    "Tap",
    "WaitFor",
    "expect",
    "quest",
]


def __getattr__(name: str) -> object:
    if name == "Context":
        from questline.authoring.context import Context

        return Context
    if name in {"Expectation", "expect"}:
        from questline.authoring import assertions as a

        return getattr(a, name)
    if name == "Page":
        from questline.authoring.pages import Page

        return Page
    if name in {"QuarantineEntry", "QuarantineLedger"}:
        from questline.authoring import quarantine as q

        return getattr(q, name)
    if name == "quest":
        from questline.authoring.markers import quest

        return quest
    if name in {
        "AssertThat",
        "HandleOptional",
        "Save",
        "Scenario",
        "Step",
        "Tap",
        "WaitFor",
    }:
        from questline.authoring import steps as s

        return getattr(s, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
