"""Run store: incremental persistence, timeline reconstruction, kill-safety."""

from __future__ import annotations

import multiprocessing as mp
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from questline.core.events import (
    EventBus,
    RunFinished,
    RunStarted,
    StepFinished,
    StepStarted,
    TestFinished,
    TestStarted,
)
from questline.core.store import RunStore


def _scripted_run(bus: EventBus, run_id: str = "run-1") -> None:
    t0 = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)
    bus.publish(RunStarted(run_id=run_id, profile="editor", timestamp=t0))
    bus.publish(
        TestStarted(
            run_id=run_id,
            test_id="test-1",
            nodeid="tests/demo.py::test_buy",
            timestamp=t0 + timedelta(seconds=1),
        )
    )
    bus.publish(
        StepStarted(
            run_id=run_id,
            test_id="test-1",
            step_id="step-1",
            name="open_shop",
            timestamp=t0 + timedelta(seconds=2),
        )
    )
    bus.publish(
        StepFinished(
            run_id=run_id,
            test_id="test-1",
            step_id="step-1",
            name="open_shop",
            status="passed",
            timestamp=t0 + timedelta(seconds=3),
        )
    )
    bus.publish(
        StepStarted(
            run_id=run_id,
            test_id="test-1",
            step_id="step-2",
            name="tap_buy",
            timestamp=t0 + timedelta(seconds=4),
        )
    )
    bus.publish(
        StepFinished(
            run_id=run_id,
            test_id="test-1",
            step_id="step-2",
            name="tap_buy",
            status="passed",
            timestamp=t0 + timedelta(seconds=5),
        )
    )
    bus.publish(
        TestFinished(
            run_id=run_id,
            test_id="test-1",
            nodeid="tests/demo.py::test_buy",
            status="passed",
            timestamp=t0 + timedelta(seconds=6),
        )
    )
    bus.publish(RunFinished(run_id=run_id, status="passed", timestamp=t0 + timedelta(seconds=7)))


def test_timeline_reconstruction(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    bus = EventBus()
    store.attach(bus)
    try:
        _scripted_run(bus)
        timeline = store.timeline("run-1")
        assert len(timeline) == 1
        test = timeline[0]
        assert test["nodeid"] == "tests/demo.py::test_buy"
        assert test["status"] == "passed"
        assert test["feature_id"] is None
        assert [s["name"] for s in test["steps"]] == ["open_shop", "tap_buy"]
        assert test["steps"][0]["started_at"].startswith("2026-07-29T12:00:02")
        assert test["steps"][1]["finished_at"].startswith("2026-07-29T12:00:05")
        run = store.get_run("run-1")
        assert run is not None
        assert run["profile"] == "editor"
        assert run["status"] == "passed"
        assert store.count_events("run-1") == 8
        assert store.ledger_path.is_file()
        lines = store.ledger_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 8
    finally:
        store.close()


def test_feature_id_persisted_and_death_point(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    bus = EventBus()
    store.attach(bus)
    try:
        t0 = datetime(2026, 7, 29, 12, 0, 0, tzinfo=UTC)
        bus.publish(RunStarted(run_id="r", profile="mock", timestamp=t0))
        bus.publish(
            TestStarted(
                run_id="r",
                test_id="t1",
                nodeid="t::a",
                feature_id="shop-pack",
                timestamp=t0,
            )
        )
        bus.publish(
            StepStarted(
                run_id="r",
                test_id="t1",
                step_id="s1",
                name="tap",
                timestamp=t0 + timedelta(seconds=1),
            )
        )
        bus.publish(
            TestFinished(
                run_id="r",
                test_id="t1",
                nodeid="t::a",
                status="failed",
                tags={"driver_alive": "true"},
                timestamp=t0 + timedelta(seconds=2),
            )
        )
        row = store.get_test("t1")
        assert row is not None
        assert row["feature_id"] == "shop-pack"
        dp = store.death_point("t1")
        assert dp["last_started_step"]["name"] == "tap"
        assert dp["driver_health"]["driver_alive"] == "true"
    finally:
        store.close()


def test_save_artifact_emits_event(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    bus = EventBus()
    store.attach(bus)
    try:
        bus.publish(RunStarted(run_id="r1", profile="editor"))
        path = store.save_artifact(b"png-bytes", run_id="r1", name="shot.png", kind="screenshot")
        assert path.read_bytes() == b"png-bytes"
        events = store.list_events("r1")
        types = [e["type"] for e in events]
        assert "ArtifactSaved" in types
    finally:
        store.close()


def test_perf_and_ai_events_persisted(tmp_path: Path) -> None:
    from questline.core.events import AiCallMade, PerfSample

    store = RunStore(tmp_path / "store.db")
    bus = EventBus()
    store.attach(bus)
    try:
        bus.publish(RunStarted(run_id="r1", profile="editor"))
        bus.publish(PerfSample(run_id="r1", test_id="t1", metric="fps", value=60.0))
        bus.publish(
            AiCallMade(
                run_id="r1",
                provider="mistral",
                model="small",
                tokens_in=10,
                tokens_out=5,
                cost=0.0,
                purpose="triage",
                duration_ms=12.5,
            )
        )
        with store._lock:  # noqa: SLF001
            perf = store._conn.execute(  # noqa: SLF001
                "SELECT metric, value FROM perf_samples WHERE run_id = ?",
                ("r1",),
            ).fetchone()
            ai = store._conn.execute(  # noqa: SLF001
                "SELECT provider, tokens_in FROM ai_calls WHERE run_id = ?",
                ("r1",),
            ).fetchone()
        assert perf["metric"] == "fps"
        assert ai["provider"] == "mistral"
        assert store.count_events() == 3
    finally:
        store.close()


def test_reattach_and_artifact_without_bus(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    bus1 = EventBus()
    bus2 = EventBus()
    store.attach(bus1)
    store.attach(bus2)
    try:
        path = store.save_artifact(
            b"x",
            run_id="r2",
            name="a.txt",
            test_id="t1",
            bus=None,
        )
        assert path.exists()
        assert store.count_events("r2") == 1
    finally:
        store.close()


def test_get_missing_run(tmp_path: Path) -> None:
    with RunStore(tmp_path / "store.db") as store:
        assert store.get_run("missing") is None


def _kill_writer(db_path: str, stop_after: int, ready: mp.synchronize.Event) -> None:
    """Child process: write events then hard-exit without cleanup."""
    store = RunStore(Path(db_path))
    bus = EventBus()
    store.attach(bus)
    bus.publish(RunStarted(run_id="kill-run", profile="ci"))
    for i in range(stop_after):
        bus.publish(
            TestStarted(
                run_id="kill-run",
                test_id=f"t-{i}",
                nodeid=f"tests/x.py::test_{i}",
            )
        )
    ready.set()
    # Ensure WAL/DB durable before simulating sudden death.
    store._conn.execute("PRAGMA wal_checkpoint(FULL)")  # noqa: SLF001
    os._exit(1)


def test_kill_safety_incremental_persistence(tmp_path: Path) -> None:
    """Simulated writer killed mid-run → store keeps all events up to the kill point."""
    db_path = tmp_path / "kill.db"
    stop_after = 5
    ready = mp.Event()
    proc = mp.Process(target=_kill_writer, args=(str(db_path), stop_after, ready))
    proc.start()
    ready.wait(timeout=30)
    proc.join(timeout=30)
    assert proc.exitcode not in (0, None)

    with RunStore(db_path) as store:
        # RunStarted + stop_after TestStarted
        assert store.count_events("kill-run") == 1 + stop_after
        run = store.get_run("kill-run")
        assert run is not None
        assert run["status"] == "running"
        tests = store.list_tests("kill-run")
        assert len(tests) == stop_after
        assert [t["id"] for t in tests] == [f"t-{i}" for i in range(stop_after)]
