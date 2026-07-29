"""Wait policy + wait_for tests, including timeout-override regression."""

from __future__ import annotations

import pytest

from questline.core.errors import TimeoutExceededError
from questline.core.waits import WaitPolicy, WaitSkipped, resolve_policy, wait_for


def test_with_overrides_preserves_unspecified_fields() -> None:
    base = WaitPolicy(probe=1.0, deadline=60.0, interval=0.25)
    overridden = base.with_overrides(deadline=90.0)
    assert overridden.probe == 1.0
    assert overridden.interval == 0.25
    assert overridden.deadline == 90.0


def test_resolve_policy_none_keeps_configured() -> None:
    configured = WaitPolicy(probe=3.0, deadline=45.0, interval=0.1)
    assert resolve_policy(configured, None) is configured


def test_timeout_override_regression_no_silent_default_reset() -> None:
    """Prove no supported API path silently resets a caller's configured timeout.

    Forbidden pattern (must NOT be used by drivers/pages):
        policy = override or WaitPolicy()
    That would replace a caller's deadline=60 with the default 15 when override is None.
    """
    caller_configured = WaitPolicy(probe=1.5, deadline=60.0, interval=0.2)

    # Correct resolution used by framework ports:
    resolved = resolve_policy(caller_configured, None)
    assert resolved.deadline == 60.0
    assert resolved.probe == 1.5

    # Partial override path:
    page = caller_configured.with_overrides(deadline=90.0)
    assert page.deadline == 90.0
    assert page.probe == 1.5
    assert page.interval == 0.2

    # The forbidden pattern (documented counter-example — must stay wrong):
    def forbidden(override: WaitPolicy | None) -> WaitPolicy:
        return override or WaitPolicy()

    silently_reset = forbidden(None)
    assert silently_reset.deadline == 15.0  # default — the bug
    assert silently_reset.deadline != caller_configured.deadline

    # Framework path must not match the bug:
    assert resolve_policy(caller_configured, None).deadline == caller_configured.deadline


def test_wait_for_success_with_fake_clock() -> None:
    ticks = {"t": 0.0}
    calls = {"n": 0}

    def clock() -> float:
        return ticks["t"]

    def sleeper(dt: float) -> None:
        ticks["t"] += dt

    def condition() -> bool:
        calls["n"] += 1
        return calls["n"] >= 3

    policy = WaitPolicy(probe=1.0, deadline=5.0, interval=0.5)
    assert wait_for(condition, policy, clock=clock, sleeper=sleeper) is True
    assert calls["n"] == 3


def test_wait_for_condition_exceptions_are_failed_probes() -> None:
    ticks = {"t": 0.0}
    calls = {"n": 0}

    def clock() -> float:
        return ticks["t"]

    def sleeper(dt: float) -> None:
        ticks["t"] += dt

    def condition() -> bool:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return True

    policy = WaitPolicy(deadline=5.0, interval=0.1)
    assert wait_for(condition, policy, clock=clock, sleeper=sleeper) is True


def test_wait_for_timeout_raise() -> None:
    ticks = {"t": 0.0}

    def clock() -> float:
        return ticks["t"]

    def sleeper(dt: float) -> None:
        ticks["t"] += dt

    with pytest.raises(TimeoutExceededError, match="deadline exceeded") as excinfo:
        wait_for(
            lambda: False, WaitPolicy(deadline=1.0, interval=0.5), clock=clock, sleeper=sleeper
        )
    assert excinfo.value.kind == "deadline"


def test_wait_for_timeout_return_false_and_skip() -> None:
    ticks = {"t": 0.0}

    def clock() -> float:
        return ticks["t"]

    def sleeper(dt: float) -> None:
        ticks["t"] += dt

    assert (
        wait_for(
            lambda: False,
            WaitPolicy(deadline=0.5, interval=0.5),
            on_timeout="return_false",
            clock=clock,
            sleeper=sleeper,
        )
        is False
    )

    ticks["t"] = 0.0
    with pytest.raises(WaitSkipped):
        wait_for(
            lambda: False,
            WaitPolicy(deadline=0.5, interval=0.5),
            on_timeout="skip",
            clock=clock,
            sleeper=sleeper,
        )
