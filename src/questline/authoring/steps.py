"""Declarative step pipeline — nothing executes before Scenario.run (architecture §4)."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from typing import Any, Protocol

from questline.authoring.assertions import Expectation
from questline.authoring.context import Context
from questline.core.errors import AuthoringError, ElementNotFoundError, QuestlineError
from questline.core.events import StepFinished, StepStarted
from questline.core.waits import WaitPolicy, resolve_policy
from questline.drivers.locators import Locator


class Step(Protocol):
    """Executable unit inside a Scenario."""

    @property
    def name(self) -> str: ...

    def execute(self, ctx: Context) -> None: ...


LocatorRef = Locator | Callable[[Context], Locator]
Predicate = Callable[[Context], Any]


def _resolve_locator(ref: LocatorRef, ctx: Context) -> Locator:
    return ref(ctx) if callable(ref) else ref


class Tap:
    """Find *locator* (deadline budget by default) and tap it."""

    def __init__(
        self,
        locator: LocatorRef,
        *,
        policy: WaitPolicy | None = None,
        budget: str = "deadline",
        name: str | None = None,
    ) -> None:
        self._locator = locator
        self._policy = policy
        self._budget = budget
        self._name = name or "Tap"

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: Context) -> None:
        locator = _resolve_locator(self._locator, ctx)
        policy = resolve_policy(ctx.wait_policy, self._policy)
        element = ctx.driver.find(locator, policy, budget=self._budget)
        ctx.driver.tap(element)


class WaitFor:
    """Wait until *locator* is present under the composed wait policy."""

    def __init__(
        self,
        locator: LocatorRef,
        *,
        policy: WaitPolicy | None = None,
        budget: str = "deadline",
        name: str | None = None,
    ) -> None:
        self._locator = locator
        self._policy = policy
        self._budget = budget
        self._name = name or "WaitFor"

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: Context) -> None:
        locator = _resolve_locator(self._locator, ctx)
        policy = resolve_policy(ctx.wait_policy, self._policy)
        ctx.driver.find(locator, policy, budget=self._budget)


class Save:
    """Evaluate *producer* and store the result under *key* in the context."""

    def __init__(
        self,
        key: str,
        producer: Callable[[Context], Any],
        *,
        name: str | None = None,
    ) -> None:
        if not key:
            raise AuthoringError("Save requires a non-empty key")
        self._key = key
        self._producer = producer
        self._name = name or f"Save({key})"

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: Context) -> None:
        ctx.save(self._key, self._producer(ctx))


class AssertThat:
    """Run an Expectation or predicate; comparator-less Expectation fails at build."""

    def __init__(
        self,
        assertion: Expectation | Predicate,
        *,
        name: str | None = None,
    ) -> None:
        if isinstance(assertion, Expectation):
            assertion.ensure_built()
        self._assertion = assertion
        self._name = name or "AssertThat"

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: Context) -> None:
        if isinstance(self._assertion, Expectation):
            self._assertion.evaluate()
            return
        result = self._assertion(ctx)
        if isinstance(result, Expectation):
            result.ensure_built()
            result.evaluate()
            return
        if result is False:
            from questline.core.errors import AssertionFailedError

            raise AssertionFailedError("AssertThat predicate returned False")


class HandleOptional:
    """Probe for an optional element; if present, run *then* steps and move on.

    Uses ``budget="probe"`` only — never the deadline budget — so unpredictable
    popups cannot burn the required-wait allowance.
    """

    def __init__(
        self,
        locator: LocatorRef,
        *then: Step | Callable[[Context], None],
        policy: WaitPolicy | None = None,
        name: str | None = None,
    ) -> None:
        self._locator = locator
        self._then = then
        self._policy = policy
        self._name = name or "HandleOptional"

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: Context) -> None:
        locator = _resolve_locator(self._locator, ctx)
        policy = resolve_policy(ctx.wait_policy, self._policy)
        try:
            element = ctx.driver.find(locator, policy, budget="probe")
        except ElementNotFoundError:
            return
        if self._then:
            for action in self._then:
                execute = getattr(action, "execute", None)
                if callable(execute):
                    execute(ctx)
                else:
                    action(ctx)  # type: ignore[operator]
        else:
            # Default dismiss: tap the optional element and move on.
            ctx.driver.tap(element)


class _CallableStep:
    """Wrap an inline callable so it is a first-class tracked step."""

    def __init__(self, fn: Callable[[Context], None], *, name: str | None = None) -> None:
        self._fn = fn
        self._name = name or getattr(fn, "__name__", "call")

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: Context) -> None:
        self._fn(ctx)


class Scenario:
    """Declarative builder: steps accumulate; nothing runs until ``.run(ctx)``."""

    def __init__(self, name: str) -> None:
        if not name:
            raise AuthoringError("Scenario requires a non-empty name")
        self.name = name
        self._steps: list[Step] = []

    def step(self, step: Step) -> Scenario:
        self._steps.append(step)
        return self

    def call(
        self,
        fn: Callable[[Context], None],
        *,
        name: str | None = None,
    ) -> Scenario:
        """Inline callable as a first-class step (execution-tracked like any other)."""
        self._steps.append(_CallableStep(fn, name=name))
        return self

    @property
    def steps(self) -> tuple[Step, ...]:
        return tuple(self._steps)

    def run(self, ctx: Context) -> None:
        """Execute steps in order, emitting StepStarted/StepFinished with real timestamps."""
        for step in self._steps:
            step_id = str(uuid.uuid4())
            step_name = f"{self.name}:{step.name}"
            started = time.perf_counter()
            ctx.bus.publish(
                StepStarted(
                    run_id=ctx.run_id,
                    test_id=ctx.test_id,
                    step_id=step_id,
                    name=step_name,
                )
            )
            status = "passed"
            error_message: str | None = None
            try:
                step.execute(ctx)
            except Exception as exc:
                status = "failed"
                error_message = str(exc) or type(exc).__name__
                duration = time.perf_counter() - started
                ctx.bus.publish(
                    StepFinished(
                        run_id=ctx.run_id,
                        test_id=ctx.test_id,
                        step_id=step_id,
                        name=step_name,
                        status=status,
                        error_message=error_message,
                        duration_s=duration,
                    )
                )
                if isinstance(exc, QuestlineError):
                    raise
                raise
            duration = time.perf_counter() - started
            ctx.bus.publish(
                StepFinished(
                    run_id=ctx.run_id,
                    test_id=ctx.test_id,
                    step_id=step_id,
                    name=step_name,
                    status=status,
                    error_message=error_message,
                    duration_s=duration,
                )
            )
