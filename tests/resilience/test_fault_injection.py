"""Fault-injection pack for phase-06 resilience (MockDriver, no device)."""

from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path

import pytest

from questline.core.errors import AssertionFailedError, SessionLostError, Verdict, classify
from questline.core.events import (
    EventBus,
    RunStarted,
    TestFinished,
    TestStarted,
)
from questline.core.exit_codes import EXIT_CIRCUIT_BREAKER, EXIT_WATCHDOG
from questline.core.health import HealthMonitor
from questline.core.recovery import RecoveryContext, RecoveryPolicy, reconnect_driver
from questline.core.store import RunStore
from questline.core.watchdog import Watchdog
from questline.drivers.handle import DriverHandle
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget

TARGET = ConnectionTarget(host="mock", port=0)


def _seed_scene() -> MockScene:
    scene = MockScene()
    scene.scene_name = "Resilience"
    root = MockNode(id="root", name="Root", path="/Root")
    scene.add(root)
    return scene


def _fresh_handle(scene: MockScene | None = None) -> DriverHandle:
    sc = scene if scene is not None else _seed_scene()

    def provider() -> MockDriver:
        return MockDriver(scene=sc)

    handle = DriverHandle(provider=provider)
    handle.connect(TARGET)
    return handle


def test_health_monitor_alive_and_hierarchy() -> None:
    handle = _fresh_handle()
    snap = HealthMonitor(handle).check()
    assert snap.driver_alive is True
    assert snap.hierarchy_ok is True
    assert snap.is_healthy is True
    handle.resolve().force_disconnect()  # type: ignore[attr-defined]
    snap2 = HealthMonitor(handle).check()
    assert snap2.driver_alive is False
    assert snap2.suggests_session_loss is True


def test_mid_step_disconnect_recovered(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db")
    store.attach(bus)
    run_id = str(uuid.uuid4())
    bus.publish(RunStarted(run_id=run_id, profile="mock"))

    scene = _seed_scene()
    driver = MockDriver(scene=scene)
    handle = DriverHandle(driver=driver, provider=lambda: MockDriver(scene=scene))
    handle.connect(TARGET)

    marks: list[str] = []

    def on_progress() -> None:
        marks.append("p")

    policy = RecoveryPolicy(
        handle,
        bus=bus,
        run_id=run_id,
        target=TARGET,
        max_consecutive_losses=5,
        on_progress=on_progress,
        abort_fn=lambda _code: None,
    )

    driver.drop_after_commands(1)
    with pytest.raises(SessionLostError) as excinfo:
        handle.hierarchy()

    recovered = policy.recover(excinfo.value)
    assert recovered is True
    assert handle.is_alive() is True
    assert marks  # progress marked during recovery

    types = [e["type"] for e in store.list_events(run_id)]
    assert "SessionLost" in types
    assert "RecoveryAttempted" in types
    assert "DriverRecovered" in types
    store.close()


def test_circuit_breaker_aborts_after_n_losses(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db")
    store.attach(bus)
    run_id = str(uuid.uuid4())
    bus.publish(RunStarted(run_id=run_id, profile="mock"))

    exits: list[int] = []
    handle = _fresh_handle()
    policy = RecoveryPolicy(
        handle,
        bus=bus,
        run_id=run_id,
        target=TARGET,
        max_consecutive_losses=3,
        abort_fn=exits.append,
        strategies=[
            (
                "always_fail",
                lambda ctx: (_ for _ in ()).throw(RuntimeError("nope")),
            )
        ],
    )

    for i in range(3):
        ok = policy.recover(SessionLostError("loss", kind="fault_inject"))
        assert ok is False
        if i < 2:
            assert not policy.tripped
        else:
            assert policy.tripped

    assert exits == [EXIT_CIRCUIT_BREAKER]
    types = [e["type"] for e in store.list_events(run_id)]
    assert types.count("SessionLost") == 3
    assert "CircuitBreakerTripped" in types
    assert "RunFinished" in types
    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "aborted"
    store.close()


def test_watchdog_fires_on_hang(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db")
    store.attach(bus)
    run_id = str(uuid.uuid4())
    bus.publish(RunStarted(run_id=run_id, profile="mock"))
    bus.publish(TestStarted(run_id=run_id, test_id="t1", nodeid="t1"))

    exits: list[int] = []
    wd = Watchdog(
        timeout_s=0.15,
        bus=bus,
        run_id=run_id,
        exit_fn=exits.append,
        poll_interval_s=0.02,
    )
    wd.start()
    # Deliberately do NOT mark progress — classic silent hang.
    deadline = time.monotonic() + 2.0
    while not wd.fired and time.monotonic() < deadline:
        time.sleep(0.02)
    wd.stop()

    assert wd.fired is True
    assert exits == [EXIT_WATCHDOG]
    types = [e["type"] for e in store.list_events(run_id)]
    assert "TestStarted" in types
    assert "WatchdogFired" in types
    assert "RunFinished" in types
    run = store.get_run(run_id)
    assert run is not None
    assert run["status"] == "aborted"
    store.close()


def test_watchdog_fires_during_hung_recovery(tmp_path: Path) -> None:
    """Classic gap: recovery must mark progress; hang inside recovery still trips watchdog."""
    bus = EventBus()
    store = RunStore(tmp_path / "store.db")
    store.attach(bus)
    run_id = str(uuid.uuid4())
    bus.publish(RunStarted(run_id=run_id, profile="mock"))

    exits: list[int] = []
    progress_marks = {"n": 0}

    wd = Watchdog(
        timeout_s=0.2,
        bus=bus,
        run_id=run_id,
        exit_fn=exits.append,
        poll_interval_s=0.02,
    )

    def on_progress() -> None:
        progress_marks["n"] += 1
        wd.mark_progress()

    hang_entered = threading.Event()

    def hung_strategy(ctx: RecoveryContext) -> None:
        ctx.progress()  # mark before hang — regression: marks fire during recovery
        hang_entered.set()
        never = threading.Event()
        never.wait(timeout=5.0)

    scene = _seed_scene()
    handle = DriverHandle(
        driver=MockDriver(scene=scene),
        provider=lambda: MockDriver(scene=scene),
    )
    handle.connect(TARGET)
    handle.resolve().force_disconnect()  # type: ignore[attr-defined]

    policy = RecoveryPolicy(
        handle,
        bus=bus,
        run_id=run_id,
        target=TARGET,
        max_consecutive_losses=10,
        on_progress=on_progress,
        abort_fn=lambda _c: None,
        strategies=[("hung", hung_strategy)],
    )

    wd.start()
    done = threading.Event()

    def _run() -> None:
        try:
            policy.recover(SessionLostError("x", kind="disconnect"))
        finally:
            done.set()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    assert hang_entered.wait(timeout=2.0)
    assert progress_marks["n"] >= 1  # marks fired during recovery before hang

    deadline = time.monotonic() + 3.0
    while not wd.fired and time.monotonic() < deadline:
        time.sleep(0.02)
    wd.stop()

    assert wd.fired is True
    assert exits == [EXIT_WATCHDOG]
    types = [e["type"] for e in store.list_events(run_id)]
    assert "SessionLost" in types
    assert "WatchdogFired" in types
    assert store.count_events(run_id) >= 2
    store.close()
    done.wait(timeout=6.0)


def test_verdict_infra_vs_test_in_store(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db")
    store.attach(bus)
    run_id = str(uuid.uuid4())
    bus.publish(RunStarted(run_id=run_id, profile="mock"))

    infra_exc = SessionLostError("gone", kind="disconnect", close_code=1006)
    bus.publish(
        TestStarted(run_id=run_id, test_id="infra_test", nodeid="infra_test")
    )
    bus.publish(
        TestFinished(
            run_id=run_id,
            test_id="infra_test",
            nodeid="infra_test",
            status="failed",
            verdict=classify(infra_exc).value,
            error_type=type(infra_exc).__name__,
            error_message=str(infra_exc),
        )
    )

    test_exc = AssertionError("plain assert failed")
    bus.publish(
        TestStarted(run_id=run_id, test_id="test_test", nodeid="test_test")
    )
    bus.publish(
        TestFinished(
            run_id=run_id,
            test_id="test_test",
            nodeid="test_test",
            status="failed",
            verdict=classify(test_exc).value,
            error_type=type(test_exc).__name__,
            error_message=str(test_exc),
        )
    )

    assert classify(AssertionFailedError("x")) is Verdict.TEST

    tests = {t["id"]: t for t in store.list_tests(run_id)}
    assert tests["infra_test"]["verdict"] == "infra"
    assert tests["infra_test"]["status"] == "failed"
    assert tests["test_test"]["verdict"] == "test"
    assert tests["test_test"]["status"] == "failed"
    store.close()


def test_reconnect_driver_strategy_uses_handle_reset() -> None:
    scene = _seed_scene()
    first = MockDriver(scene=scene)
    created: list[MockDriver] = []

    def provider() -> MockDriver:
        d = MockDriver(scene=scene)
        created.append(d)
        return d

    handle = DriverHandle(driver=first, provider=provider)
    handle.connect(TARGET)
    first.force_disconnect()
    assert handle.is_alive() is False

    marks: list[int] = []
    ctx = RecoveryContext(
        handle=handle,
        target=TARGET,
        mark_progress=lambda: marks.append(1),
    )
    reconnect_driver(ctx)
    assert handle.is_alive() is True
    assert created  # fresh driver via provider after reset
    assert marks
