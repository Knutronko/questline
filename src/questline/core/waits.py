"""Wait policy and the single wait primitive (architecture §2.5)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Literal, TypeVar

from questline.core.errors import TimeoutExceededError

T = TypeVar("T")

OnTimeout = Literal["raise", "skip", "return_false"]


class WaitSkipped(Exception):
    """Raised when wait_for times out with on_timeout='skip'.

    The authoring layer (Phase 03) maps this to pytest.skip.
    """


@dataclass(frozen=True, slots=True)
class WaitPolicy:
    """probe = single presence check; deadline = total budget; interval = poll period."""

    probe: float = 2.0
    deadline: float = 15.0
    interval: float = 0.5

    def with_overrides(
        self,
        *,
        probe: float | None = None,
        deadline: float | None = None,
        interval: float | None = None,
    ) -> WaitPolicy:
        """Return a copy overriding only explicitly provided fields.

        ``None`` means "keep this policy's value". This is the only supported way to
        apply a *partial* override. Rebuilding ``WaitPolicy(deadline=X)`` from scratch
        would silently reset ``probe``/``interval`` to defaults — that is a bug.
        """
        return replace(
            self,
            probe=self.probe if probe is None else probe,
            deadline=self.deadline if deadline is None else deadline,
            interval=self.interval if interval is None else interval,
        )


def resolve_policy(configured: WaitPolicy, override: WaitPolicy | None) -> WaitPolicy:
    """Resolve profile < page < step without silently resetting *configured*.

    When *override* is None, returns *configured* unchanged. Never substitutes a fresh
    ``WaitPolicy()`` default — that pattern is forbidden and regression-tested.
    """
    if override is None:
        return configured
    return override


def wait_for(
    condition: Callable[[], T | bool],
    policy: WaitPolicy,
    *,
    on_timeout: OnTimeout = "raise",
    clock: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> T | bool:
    """Poll *condition* until truthy or *policy.deadline* elapses.

    Exceptions from *condition* count as failed probes (retries continue).
    Uses *policy.deadline* as the total budget; *policy.interval* between probes.
    """
    deadline_at = clock() + policy.deadline
    last_exc: BaseException | None = None

    while True:
        try:
            result = condition()
            if result:
                return result
        except Exception as exc:
            last_exc = exc

        now = clock()
        if now >= deadline_at:
            return _handle_timeout(on_timeout, policy, last_exc)

        remaining = deadline_at - now
        sleeper(min(policy.interval, remaining))


def _handle_timeout(
    on_timeout: OnTimeout,
    policy: WaitPolicy,
    last_exc: BaseException | None,
) -> bool:
    detail = f" after {policy.deadline}s"
    if last_exc is not None:
        detail += f" (last probe error: {last_exc!r})"

    if on_timeout == "return_false":
        return False
    if on_timeout == "skip":
        raise WaitSkipped(f"wait skipped{detail}")
    raise TimeoutExceededError(
        f"deadline exceeded{detail}",
        kind="deadline",
    )
