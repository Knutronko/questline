"""Authoring expect() — comparator required at build time."""

from __future__ import annotations

import pytest

from questline.authoring.assertions import expect
from questline.authoring.steps import AssertThat
from questline.core.errors import AssertionFailedError, AuthoringError


def test_comparator_less_expect_fails_at_build_time() -> None:
    with pytest.raises(AuthoringError, match="requires a comparator"):
        AssertThat(expect(1))


def test_equals_passes_and_fails() -> None:
    expect(3).equals(3).evaluate()
    with pytest.raises(AssertionFailedError, match="expected 2"):
        expect(3).equals(2).evaluate()


def test_differs_contains_is_true_is_false() -> None:
    expect(1).differs(2).evaluate()
    expect([1, 2]).contains(1).evaluate()
    expect(True).is_true().evaluate()
    expect(False).is_false().evaluate()
    with pytest.raises(AssertionFailedError):
        expect(0).is_true().evaluate()
    with pytest.raises(AssertionFailedError):
        expect([1]).contains(9).evaluate()
    with pytest.raises(AssertionFailedError):
        expect(1).contains(1).evaluate()


def test_ensure_built_on_bare_expectation() -> None:
    bare = expect("x")
    assert bare.has_comparator is False
    with pytest.raises(AuthoringError, match="requires a comparator"):
        bare.ensure_built()
