"""Threshold assertions + seeded low-FPS failure with series artifact."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.errors import AssertionFailedError, Verdict, classify
from questline.core.events import EventBus, PerfSample, RunStarted
from questline.core.store import RunStore
from questline.perf import assert_avg, assert_max, assert_no_samples_below
from questline.perf.asserts import PerfAssertContext, bind_perf_context, clear_perf_context


@pytest.fixture
def seeded_store(tmp_path: Path) -> RunStore:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "artifacts")
    store.attach(bus)
    bus.publish(RunStarted(run_id="run-low", profile="ci"))
    # Seeded low-FPS series (demo acceptance).
    for i, fps in enumerate([12.0, 15.0, 10.0, 18.0, 14.0]):
        bus.publish(PerfSample(run_id="run-low", test_id="test::low_fps", metric="fps", value=fps))
        _ = i
    bus.publish(
        PerfSample(run_id="run-low", test_id="test::low_fps", metric="memory_pss_mb", value=200.0)
    )
    bus.publish(
        PerfSample(run_id="run-low", test_id="test::low_fps", metric="memory_pss_mb", value=210.0)
    )
    bind_perf_context(
        PerfAssertContext(store=store, bus=bus, run_id="run-low", test_id="test::low_fps")
    )
    yield store
    clear_perf_context()
    store.close()


def test_assert_avg_fails_with_series_artifact(seeded_store: RunStore) -> None:
    with pytest.raises(AssertionFailedError) as excinfo:
        assert_avg("fps", ">=", 55, scope="test")
    err = excinfo.value
    assert classify(err) == Verdict.TEST
    assert "series=" in str(err)
    arts = seeded_store.list_artifacts(run_id="run-low", test_id="test::low_fps")
    kinds = {a.get("kind") for a in arts}
    assert "perf_series" in kinds
    # Artifact file exists and contains the series.
    paths = [Path(a["path"]) for a in arts if a.get("kind") == "perf_series"]
    assert paths and paths[0].is_file()
    body = paths[0].read_text(encoding="utf-8")
    assert '"metric": "fps"' in body
    assert "12.0" in body


def test_assert_max_memory(seeded_store: RunStore) -> None:
    with pytest.raises(AssertionFailedError):
        assert_max("memory_pss_mb", "<=", 150, scope="test")
    # Passes when threshold is high enough.
    peak = assert_max("memory_pss_mb", "<=", 250, scope="test")
    assert peak == 210.0


def test_assert_no_samples_below_with_tolerance(seeded_store: RunStore) -> None:
    with pytest.raises(AssertionFailedError):
        assert_no_samples_below("fps", 20, tolerance=0, scope="test")
    # All five samples are below 20 — tolerance=4 still fails (5 > 4).
    with pytest.raises(AssertionFailedError):
        assert_no_samples_below("fps", 20, tolerance=4, scope="test")
    assert assert_no_samples_below("fps", 20, tolerance=5, scope="test") == 5


def test_assert_avg_passes_on_healthy_series(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "artifacts")
    store.attach(bus)
    for v in (58.0, 60.0, 62.0):
        bus.publish(PerfSample(run_id="r", test_id="t", metric="fps", value=v))
    bind_perf_context(PerfAssertContext(store=store, bus=bus, run_id="r", test_id="t"))
    try:
        avg = assert_avg("fps", ">=", 55, scope="test")
        assert avg == 60.0
    finally:
        clear_perf_context()
        store.close()
