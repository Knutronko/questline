"""Seedable demo store for HUD CI / Playwright smoke."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from questline.core.events import (
    EventBus,
    PerfSample,
    RunFinished,
    RunStarted,
    StepFinished,
    StepStarted,
    TestFinished,
    TestStarted,
)
from questline.core.store import RunStore


def seed_fixture_store(db_path: Path) -> RunStore:
    """Populate a store with two runs suitable for API + Playwright smoke."""
    store = RunStore(db_path)
    bus = EventBus()
    store.attach(bus)
    t0 = datetime(2026, 8, 10, 10, 0, 0, tzinfo=UTC)

    bus.publish(
        RunStarted(
            run_id="run-a",
            profile="android_local",
            timestamp=t0,
            tags={"driver": "questline", "device": "adb"},
        )
    )
    bus.publish(
        TestStarted(
            run_id="run-a",
            test_id="t-pass",
            nodeid="tests/demo.py::test_boot",
            timestamp=t0 + timedelta(seconds=1),
        )
    )
    bus.publish(
        StepStarted(
            run_id="run-a",
            test_id="t-pass",
            step_id="s1",
            name="wait_hello",
            timestamp=t0 + timedelta(seconds=2),
        )
    )
    bus.publish(
        StepFinished(
            run_id="run-a",
            test_id="t-pass",
            step_id="s1",
            name="wait_hello",
            status="passed",
            timestamp=t0 + timedelta(seconds=3),
        )
    )
    bus.publish(
        TestFinished(
            run_id="run-a",
            test_id="t-pass",
            nodeid="tests/demo.py::test_boot",
            status="passed",
            timestamp=t0 + timedelta(seconds=4),
        )
    )
    bus.publish(
        TestStarted(
            run_id="run-a",
            test_id="t-infra",
            nodeid="tests/demo.py::test_shop",
            timestamp=t0 + timedelta(seconds=5),
        )
    )
    bus.publish(
        StepStarted(
            run_id="run-a",
            test_id="t-infra",
            step_id="s2",
            name="open_shop",
            timestamp=t0 + timedelta(seconds=6),
        )
    )
    bus.publish(
        TestFinished(
            run_id="run-a",
            test_id="t-infra",
            nodeid="tests/demo.py::test_shop",
            status="failed",
            verdict="infra",
            error_type="SessionLostError",
            error_message="socket closed",
            timestamp=t0 + timedelta(seconds=7),
            tags={"health": "lost"},
        )
    )
    shot = store.save_artifact(
        b"fakepng",
        run_id="run-a",
        test_id="t-infra",
        name="fail.png",
        kind="screenshot",
        bus=bus,
    )
    assert shot.exists()
    bus.publish(
        RunFinished(run_id="run-a", status="failed", timestamp=t0 + timedelta(seconds=8))
    )

    # Perf samples for HUD graphs / compare (phase-10).
    for i, fps in enumerate((58.0, 60.0, 55.0, 57.0)):
        bus.publish(
            PerfSample(
                run_id="run-a",
                test_id="t-pass",
                metric="fps",
                value=fps,
                timestamp=t0 + timedelta(seconds=2 + i),
            )
        )
    for i, mem in enumerate((210.0, 215.0, 220.0)):
        bus.publish(
            PerfSample(
                run_id="run-a",
                test_id="t-pass",
                metric="memory_pss_mb",
                value=mem,
                timestamp=t0 + timedelta(seconds=2 + i),
            )
        )

    t1 = t0 + timedelta(hours=1)
    bus.publish(
        RunStarted(
            run_id="run-b",
            profile="editor",
            timestamp=t1,
            tags={"driver": "mock"},
        )
    )
    bus.publish(
        TestStarted(
            run_id="run-b",
            test_id="t-shop-b",
            nodeid="tests/demo.py::test_shop",
            timestamp=t1 + timedelta(seconds=1),
        )
    )
    bus.publish(
        StepStarted(
            run_id="run-b",
            test_id="t-shop-b",
            step_id="s3",
            name="open_shop",
            timestamp=t1 + timedelta(seconds=2),
        )
    )
    bus.publish(
        StepFinished(
            run_id="run-b",
            test_id="t-shop-b",
            step_id="s3",
            name="open_shop",
            status="passed",
            timestamp=t1 + timedelta(seconds=3),
        )
    )
    bus.publish(
        TestFinished(
            run_id="run-b",
            test_id="t-shop-b",
            nodeid="tests/demo.py::test_shop",
            status="passed",
            timestamp=t1 + timedelta(seconds=4),
        )
    )
    bus.publish(
        RunFinished(run_id="run-b", status="passed", timestamp=t1 + timedelta(seconds=5))
    )

    for i, fps in enumerate((50.0, 52.0, 49.0, 51.0)):
        bus.publish(
            PerfSample(
                run_id="run-b",
                test_id="t-shop-b",
                metric="fps",
                value=fps,
                timestamp=t1 + timedelta(seconds=1 + i),
            )
        )
    for i, mem in enumerate((230.0, 240.0, 235.0)):
        bus.publish(
            PerfSample(
                run_id="run-b",
                test_id="t-shop-b",
                metric="memory_pss_mb",
                value=mem,
                timestamp=t1 + timedelta(seconds=1 + i),
            )
        )

    store.detach()
    return store
