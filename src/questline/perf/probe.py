"""Background PerfProbe sampler thread (architecture §7)."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Protocol

from questline.core.events import EventBus, PerfSample

logger = logging.getLogger("questline.perf.probe")

CollectorFn = Callable[[], Mapping[str, float]]


class MetricCollector(Protocol):
    """Callable or object that returns metric_name → value (omit unavailable)."""

    def collect(self) -> Mapping[str, float]: ...


def _invoke_collector(collector: MetricCollector | CollectorFn) -> Mapping[str, float]:
    if hasattr(collector, "collect"):
        return collector.collect()  # type: ignore[union-attr]
    return collector()  # type: ignore[operator]


class PerfProbe:
    """Daemon sampler that publishes ``PerfSample`` events incrementally.

    Each sample is published on the bus immediately so the store commits it in
    its own transaction — a hard kill mid-run still retains prior samples.
    Collector failures are logged and skipped (metric unavailable); they never
    stop the sampler or fail the run.
    """

    def __init__(
        self,
        *,
        bus: EventBus,
        run_id: str,
        collectors: Sequence[MetricCollector | CollectorFn],
        interval_s: float = 1.0,
        metrics: Sequence[str] | None = None,
        sleeper: Callable[[float], None] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if interval_s <= 0:
            raise ValueError("interval_s must be > 0")
        self._bus = bus
        self._run_id = run_id
        self._collectors = list(collectors)
        self._interval_s = float(interval_s)
        self._metrics = frozenset(metrics) if metrics is not None else None
        self._sleeper = sleeper or time.sleep
        self._clock = clock or time.monotonic
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._test_id: str | None = None
        self._test_lock = threading.Lock()
        self._sample_count = 0
        self._error_count = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def sample_count(self) -> int:
        return self._sample_count

    @property
    def error_count(self) -> int:
        return self._error_count

    def set_test_id(self, test_id: str | None) -> None:
        with self._test_lock:
            self._test_id = test_id

    def start(self, *, test_id: str | None = None) -> None:
        """Start the background sampler (no-op if already running)."""
        if self.running:
            if test_id is not None:
                self.set_test_id(test_id)
            return
        self._stop.clear()
        if test_id is not None:
            self.set_test_id(test_id)
        thread = threading.Thread(
            target=self._loop,
            name="questline-perf-probe",
            daemon=True,
        )
        self._thread = thread
        thread.start()
        logger.info(
            "PerfProbe started run_id=%s interval_s=%.3f collectors=%d",
            self._run_id,
            self._interval_s,
            len(self._collectors),
        )

    def stop(self, *, join_timeout_s: float = 2.0) -> None:
        """Signal stop and join the sampler thread (best-effort)."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=join_timeout_s)
            if thread.is_alive():
                logger.warning(
                    "PerfProbe thread did not stop within %.1fs (daemon; will die with process)",
                    join_timeout_s,
                )
        self._thread = None
        logger.info(
            "PerfProbe stopped run_id=%s samples=%d collector_errors=%d",
            self._run_id,
            self._sample_count,
            self._error_count,
        )

    def kill(self) -> None:
        """Alias for abrupt stop — same as ``stop`` (daemon + incremental writes)."""
        self.stop(join_timeout_s=0.1)

    def sample_once(self) -> int:
        """Collect and publish one round (used by tests and the loop). Returns published count."""
        with self._test_lock:
            test_id = self._test_id
        published = 0
        for collector in self._collectors:
            try:
                values = _invoke_collector(collector)
            except Exception as exc:
                self._error_count += 1
                logger.warning(
                    "PerfProbe collector failed (%s): %s — metric(s) unavailable this tick",
                    type(exc).__name__,
                    exc,
                )
                continue
            if not values:
                continue
            for metric, value in values.items():
                if self._metrics is not None and metric not in self._metrics:
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    self._error_count += 1
                    logger.warning(
                        "PerfProbe skipping non-numeric %s=%r",
                        metric,
                        value,
                    )
                    continue
                self._bus.publish(
                    PerfSample(
                        run_id=self._run_id,
                        test_id=test_id,
                        metric=metric,
                        value=numeric,
                    )
                )
                published += 1
                self._sample_count += 1
        return published

    def _loop(self) -> None:
        # First sample immediately so short tests still get a point.
        self.sample_once()
        while not self._stop.wait(self._interval_s):
            t0 = self._clock()
            self.sample_once()
            elapsed = self._clock() - t0
            if elapsed > self._interval_s * 0.5:
                logger.debug(
                    "PerfProbe sample tick took %.3fs (interval=%.3fs) — overhead note",
                    elapsed,
                    self._interval_s,
                )
