"""Fluent assertions — comparator required at build time (architecture §4)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from questline.core.errors import AssertionFailedError, AuthoringError


class Expectation:
    """Builder for a single comparison. Must select a comparator before use."""

    def __init__(self, actual: Any) -> None:
        self._actual = actual
        self._check: Callable[[], None] | None = None
        self._description: str | None = None

    @property
    def has_comparator(self) -> bool:
        return self._check is not None

    def equals(self, expected: Any) -> Expectation:
        actual = self._actual

        def _check() -> None:
            if actual != expected:
                raise AssertionFailedError(f"expected {expected!r}, got {actual!r}")

        self._check = _check
        self._description = f"equals({expected!r})"
        return self

    def differs(self, expected: Any) -> Expectation:
        actual = self._actual

        def _check() -> None:
            if actual == expected:
                raise AssertionFailedError(f"expected value to differ from {expected!r}")

        self._check = _check
        self._description = f"differs({expected!r})"
        return self

    def is_true(self) -> Expectation:
        actual = self._actual

        def _check() -> None:
            if not actual:
                raise AssertionFailedError(f"expected true-ish value, got {actual!r}")

        self._check = _check
        self._description = "is_true()"
        return self

    def is_false(self) -> Expectation:
        actual = self._actual

        def _check() -> None:
            if actual:
                raise AssertionFailedError(f"expected false-ish value, got {actual!r}")

        self._check = _check
        self._description = "is_false()"
        return self

    def contains(self, item: Any) -> Expectation:
        actual = self._actual

        def _check() -> None:
            try:
                ok = item in actual
            except TypeError as exc:
                raise AssertionFailedError(
                    f"cannot check contains({item!r}) on {type(actual).__name__}"
                ) from exc
            if not ok:
                raise AssertionFailedError(f"expected {actual!r} to contain {item!r}")

        self._check = _check
        self._description = f"contains({item!r})"
        return self

    def ensure_built(self) -> None:
        """Raise AuthoringError if no comparator was selected (build-time hard fail)."""
        if self._check is None:
            raise AuthoringError(
                "expect(...) requires a comparator before use "
                "(e.g. .equals(x), .differs(x), .is_true(), .contains(x)). "
                "Constructing an assertion with no comparison is an authoring error."
            )

    def evaluate(self) -> None:
        self.ensure_built()
        assert self._check is not None
        self._check()

    def __repr__(self) -> str:
        cmp = self._description or "(no comparator)"
        return f"Expectation({self._actual!r}).{cmp}"


def expect(actual: Any) -> Expectation:
    """Start a fluent assertion. A comparator must be chained before evaluation."""
    return Expectation(actual)
