"""PerfProbe sampler lifecycle unit tests."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from questline.core.events import EventBus, PerfSample
from questline.core.store import RunStore
from questline.perf.probe import PerfProbe


def test_probe_start_stop_publishes_samples(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "artifacts")
    store.attach(bus)
    ticks = {"n": 0}
    gate = threading.Event()

    def collector() -> dict[str, float]:
        ticks["n"] += 1
        if ticks["n"] >= 2:
            gate.set()
        return {"fps": 55.0 + ticks["n"]}

    probe = PerfProbe(
        bus=bus,
        run_id="run-1",
        collectors=[collector],
        interval_s=0.05,
        metrics=["fps"],
    )
    probe.start(test_id="t1")
    assert gate.wait(timeout=2.0)
    probe.stop()
    assert not probe.running
    rows = store.list_perf_samples(run_id="run-1", metric="fps")
    assert len(rows) >= 2
    assert all(r["test_id"] == "t1" for r in rows)
    store.close()


def test_probe_kill_keeps_prior_samples(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "artifacts")
    store.attach(bus)
    published: list[PerfSample] = []
    bus.subscribe(lambda e: published.append(e) if isinstance(e, PerfSample) else None)

    def collector() -> dict[str, float]:
        return {"fps": 40.0}

    probe = PerfProbe(
        bus=bus,
        run_id="run-k",
        collectors=[collector],
        interval_s=10.0,  # long interval; first sample is immediate
    )
    probe.start(test_id="tk")
    time.sleep(0.05)
    probe.kill()
    assert len(published) >= 1
    rows = store.list_perf_samples(run_id="run-k")
    assert len(rows) >= 1
    store.close()


def test_collector_failure_does_not_stop_sampler(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "artifacts")
    store.attach(bus)
    state = {"fail": True}

    def bad() -> dict[str, float]:
        if state["fail"]:
            state["fail"] = False
            raise RuntimeError("boom")
        return {"fps": 60.0}

    probe = PerfProbe(bus=bus, run_id="run-e", collectors=[bad], interval_s=1.0)
    assert probe.sample_once() == 0
    assert probe.error_count >= 1
    assert probe.sample_once() == 1
    rows = store.list_perf_samples(run_id="run-e")
    assert len(rows) == 1
    store.close()
