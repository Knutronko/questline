"""No-progress watchdog daemon (architecture §2.6)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from questline.core.events import EventBus, RunFinished, WatchdogFired
from questline.core.exit_codes import EXIT_WATCHDOG


class Watchdog:
    """Daemon timer that aborts when no progress is marked within *timeout_s*.

    Every long operation — including recovery — must call ``mark_progress()``.
    On fire: emit ``WatchdogFired``, optionally seal the run, then invoke
    ``exit_fn`` (default: ``os._exit``) with ``EXIT_WATCHDOG``.
    """

    def __init__(
        self,
        *,
        timeout_s: float = 120.0,
        bus: EventBus | None = None,
        run_id: str | None = None,
        exit_fn: Callable[[int], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
        poll_interval_s: float = 0.05,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("watchdog timeout_s must be > 0")
        self.timeout_s = timeout_s
        self._bus = bus
        self._run_id = run_id
        self._exit_fn = exit_fn
        self._clock = clock
        self._poll_interval_s = poll_interval_s
        self._last_progress = clock()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._fired = threading.Event()
        self._thread: threading.Thread | None = None
        self._exit_code: int | None = None
        self._run_sealed = False

    @property
    def fired(self) -> bool:
        return self._fired.is_set()

    @property
    def exit_code(self) -> int | None:
        return self._exit_code

    def mark_progress(self) -> None:
        """Reset the no-progress timer. Call from every long operation."""
        with self._lock:
            self._last_progress = self._clock()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._fired.clear()
        self._exit_code = None
        self.mark_progress()
        self._thread = threading.Thread(
            target=self._loop,
            name="questline-watchdog",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=max(1.0, self._poll_interval_s * 20))
        self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                age = self._clock() - self._last_progress
            if age >= self.timeout_s:
                self._fire(age)
                return
            self._stop.wait(self._poll_interval_s)

    def _fire(self, age: float) -> None:
        if self._fired.is_set():
            return
        self._fired.set()
        self._exit_code = EXIT_WATCHDOG
        if self._bus is not None and self._run_id is not None:
            self._bus.publish(
                WatchdogFired(
                    run_id=self._run_id,
                    timeout_s=self.timeout_s,
                    last_progress_age_s=age,
                )
            )
            if not self._run_sealed:
                self._bus.publish(
                    RunFinished(
                        run_id=self._run_id,
                        status="aborted",
                        duration_s=None,
                    )
                )
                self._run_sealed = True
        exit_fn = self._exit_fn
        if exit_fn is not None:
            exit_fn(EXIT_WATCHDOG)
        else:
            # Production default: hard exit so a hung main thread cannot ignore us.
            import os

            os._exit(EXIT_WATCHDOG)  # noqa: S106 — intentional process abort


__all__ = ["Watchdog"]
