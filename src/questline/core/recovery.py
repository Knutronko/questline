"""Session-loss recovery ladder + circuit breaker (architecture §2.6)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from questline.core.errors import SessionLostError
from questline.core.events import (
    CircuitBreakerTripped,
    DriverRecovered,
    EventBus,
    RecoveryAttempted,
    RunFinished,
    SessionLost,
)
from questline.core.exit_codes import EXIT_CIRCUIT_BREAKER
from questline.drivers.port import ConnectionTarget

if TYPE_CHECKING:
    from questline.drivers.handle import DriverHandle

StrategyFn = Callable[["RecoveryContext"], None]
ProgressFn = Callable[[], None]
AbortFn = Callable[[int], Any]


@dataclass
class RecoveryContext:
    """Mutable context passed to recovery strategies."""

    handle: DriverHandle
    target: ConnectionTarget
    device_provider: Any | None = None
    device: Any | None = None
    app_package: str | None = None
    app_activity: str | None = None
    mark_progress: ProgressFn | None = None

    def progress(self) -> None:
        if self.mark_progress is not None:
            self.mark_progress()


class CircuitBreakerOpen(RuntimeError):
    """Raised after the consecutive-loss threshold is reached (when abort_fn is None)."""

    def __init__(self, consecutive_losses: int, threshold: int) -> None:
        super().__init__(
            f"circuit breaker open after {consecutive_losses} consecutive session losses "
            f"(threshold={threshold})"
        )
        self.consecutive_losses = consecutive_losses
        self.threshold = threshold
        self.exit_code = EXIT_CIRCUIT_BREAKER


class RecoveryPolicy:
    """Ordered strategies: reconnect_driver → restart_app → restart_session.

    Never freezes a raw driver reference — all swaps go through ``DriverHandle.reset``.
    """

    def __init__(
        self,
        handle: DriverHandle,
        *,
        bus: EventBus,
        run_id: str,
        target: ConnectionTarget | None = None,
        device_provider: Any | None = None,
        device: Any | None = None,
        app_package: str | None = None,
        app_activity: str | None = None,
        max_consecutive_losses: int = 3,
        on_progress: ProgressFn | None = None,
        abort_fn: AbortFn | None = None,
        strategies: list[tuple[str, StrategyFn]] | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._handle = handle
        self._bus = bus
        self._run_id = run_id
        self._target = target or ConnectionTarget()
        self._device_provider = device_provider
        self._device = device
        self._app_package = app_package
        self._app_activity = app_activity
        self._max_consecutive_losses = max(1, max_consecutive_losses)
        self._on_progress = on_progress
        self._abort_fn = abort_fn
        self._clock = clock
        self._consecutive_losses = 0
        self._tripped = False
        self._strategies = strategies or [
            ("reconnect_driver", reconnect_driver),
            ("restart_app", restart_app),
            ("restart_session", restart_session),
        ]

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    @property
    def tripped(self) -> bool:
        return self._tripped

    def record_pass(self) -> None:
        """An intervening pass resets the consecutive-loss counter."""
        self._consecutive_losses = 0

    def record_loss(
        self,
        exc: BaseException | None = None,
        *,
        kind: str | None = None,
        close_code: int | None = None,
    ) -> None:
        """Record a session loss, emit ``SessionLost``, and trip the breaker if needed."""
        loss_kind = kind or "unknown"
        code = close_code
        if isinstance(exc, SessionLostError):
            loss_kind = exc.kind or loss_kind
            code = exc.close_code if code is None else code
        self._bus.publish(
            SessionLost(run_id=self._run_id, kind=loss_kind, close_code=code)
        )
        self._consecutive_losses += 1
        if self._consecutive_losses >= self._max_consecutive_losses:
            self._trip()

    def recover(self, exc: BaseException | None = None) -> bool:
        """Run the recovery ladder. Returns True if a strategy restored the session.

        Emits ``SessionLost`` once (via ``record_loss``). Does not auto-retry the
        failed test — caller keeps pytest outcome failed.
        """
        if self._tripped:
            return False

        # Count this recovery cycle as a loss for the breaker (pass resets it).
        self.record_loss(exc)

        if self._tripped:
            return False

        ctx = RecoveryContext(
            handle=self._handle,
            target=self._target,
            device_provider=self._device_provider,
            device=self._device,
            app_package=self._app_package,
            app_activity=self._app_activity,
            mark_progress=self._on_progress,
        )

        for name, strategy in self._strategies:
            ctx.progress()
            t0 = self._clock()
            error_message: str | None = None
            success = False
            try:
                strategy(ctx)
                ctx.progress()
                try:
                    success = bool(self._handle.is_alive())
                except Exception as alive_exc:
                    error_message = f"{type(alive_exc).__name__}: {alive_exc}"
                    success = False
                if not success and error_message is None:
                    error_message = "driver not alive after strategy"
            except Exception as strategy_exc:
                error_message = f"{type(strategy_exc).__name__}: {strategy_exc}"
                success = False

            duration = self._clock() - t0
            self._bus.publish(
                RecoveryAttempted(
                    run_id=self._run_id,
                    strategy=name,
                    success=success,
                    duration_s=duration,
                    error_message=error_message,
                )
            )
            if success:
                self._bus.publish(
                    DriverRecovered(
                        run_id=self._run_id,
                        strategy=name,
                        duration_s=duration,
                    )
                )
                return True
        return False

    def _trip(self) -> None:
        if self._tripped:
            return
        self._tripped = True
        self._bus.publish(
            CircuitBreakerTripped(
                run_id=self._run_id,
                consecutive_losses=self._consecutive_losses,
                threshold=self._max_consecutive_losses,
            )
        )
        self._bus.publish(
            RunFinished(
                run_id=self._run_id,
                status="aborted",
                duration_s=None,
            )
        )
        if self._abort_fn is not None:
            self._abort_fn(EXIT_CIRCUIT_BREAKER)
        else:
            raise CircuitBreakerOpen(
                self._consecutive_losses,
                self._max_consecutive_losses,
            )


def reconnect_driver(ctx: RecoveryContext) -> None:
    """Cheap reconnect via handle reset + connect (never freeze a raw driver ref)."""
    ctx.progress()
    ctx.handle.reset()
    ctx.progress()
    ctx.handle.connect(ctx.target)
    ctx.progress()


def restart_app(ctx: RecoveryContext) -> None:
    """Force-stop + launch the app on device, then reconnect the driver."""
    ctx.progress()
    provider = ctx.device_provider
    device = ctx.device
    package = ctx.app_package
    if provider is None or device is None or not package:
        raise RuntimeError("restart_app skipped: no device/package configured")
    provider.stop(device, package=package)
    ctx.progress()
    provider.launch(device, package=package, activity=ctx.app_activity)
    ctx.progress()
    ctx.handle.reset()
    ctx.progress()
    ctx.handle.connect(ctx.target)
    ctx.progress()


def restart_session(ctx: RecoveryContext) -> None:
    """Full session relaunch: optional app restart + fresh driver session."""
    ctx.progress()
    provider = ctx.device_provider
    device = ctx.device
    package = ctx.app_package
    if provider is not None and device is not None and package:
        try:
            provider.stop(device, package=package)
            ctx.progress()
            provider.launch(device, package=package, activity=ctx.app_activity)
            ctx.progress()
        except Exception:
            ctx.progress()
    ctx.handle.reset()
    ctx.progress()
    ctx.handle.connect(ctx.target)
    ctx.progress()


__all__ = [
    "CircuitBreakerOpen",
    "RecoveryContext",
    "RecoveryPolicy",
    "reconnect_driver",
    "restart_app",
    "restart_session",
]
