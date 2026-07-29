"""Phase-03 acceptance meta-tests: demo timeline, death-point, quarantine audit."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from questline.authoring.context import Context
from questline.authoring.quarantine import QuarantineLedger, collect_quarantined_nodeids
from questline.authoring.steps import Scenario, Tap
from questline.core.errors import ElementNotFoundError
from questline.core.events import EventBus, RunStarted, TestFinished, TestStarted
from questline.core.store import RunStore
from questline.core.waits import WaitPolicy
from questline.drivers.handle import DriverHandle
from questline.drivers.locators import Locator, LocatorStrategy
from questline.drivers.mock import MockDriver
from questline.drivers.mock.scene import MockNode, MockScene
from questline.drivers.port import ConnectionTarget

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo-tests"


def _norm(nodeid: str) -> str:
    return nodeid.replace("\\", "/")


def test_demo_suite_green_and_store_timeline(tmp_path: Path) -> None:
    """Acceptance: pytest examples/demo-tests --questline-profile mock is green + timeline."""
    import shutil

    proj = tmp_path / "demo_proj"
    proj.mkdir()
    # Isolate store from the in-process session fixture DB under the repo root.
    shutil.copy(ROOT / "examples" / "questline.toml", proj / "questline.toml")
    demo_dest = proj / "demo-tests"
    shutil.copytree(DEMO, demo_dest)
    # Locators package lives next to examples/
    shutil.copy(ROOT / "examples" / "generated_locators.py", proj / "generated_locators.py")
    # Nodeids are relative to --rootdir (proj), so rewrite the ledger entry.
    ledger_path = demo_dest / "quarantine.yaml"
    ledger_path.write_text(
        "version: 1\nentries:\n"
        "  - test_id: demo-tests/test_demo_game.py::test_flaky_buy_quarantined\n"
        "    reason: seed\n"
        "    date: '2026-07-29'\n"
        "    owner: ci\n"
        "    exit_criteria: n/a\n"
        "    feature: demo-shop\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(demo_dest),
        "--questline-profile=mock",
        f"--questline-config={proj / 'questline.toml'}",
        f"--questline-quarantine={demo_dest / 'quarantine.yaml'}",
        "--rootdir",
        str(proj),
        "-q",
        "-o",
        "addopts=",
    ]
    proc = subprocess.run(cmd, cwd=str(proj), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    store_db = proj / ".questline" / "store.db"
    assert store_db.is_file()
    with RunStore(store_db) as store:
        conn = sqlite3.connect(str(store_db))
        run = conn.execute(
            "SELECT id, status FROM runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert run is not None
        run_id, status = run[0], run[1]
        assert status == "passed"
        timeline = store.timeline(run_id)
        assert len(timeline) >= 7  # quarantined excluded by default
        with_steps = [t for t in timeline if t["steps"]]
        assert with_steps, "expected Scenario-driven tests to persist steps"
        featured = [t for t in timeline if t.get("feature_id")]
        assert featured, "expected feature_id on tagged demo tests"


def test_death_point_last_started_step_and_driver_health(tmp_path: Path) -> None:
    scene = MockScene()
    scene.add(MockNode(id="ok", name="Ok"))
    driver = MockDriver(scene)
    driver.connect(ConnectionTarget())
    bus = EventBus()
    store = RunStore(tmp_path / "store.db")
    store.attach(bus)
    run_id = "death-run"
    test_id = "death-test"

    bus.publish(RunStarted(run_id=run_id, profile="mock"))
    bus.publish(TestStarted(run_id=run_id, test_id=test_id, nodeid=test_id, feature_id="x"))

    ctx = Context(
        driver=DriverHandle(driver),
        bus=bus,
        run_id=run_id,
        test_id=test_id,
        wait_policy=WaitPolicy(probe=0.05, deadline=0.2, interval=0.01),
    )
    scenario = (
        Scenario("die")
        .step(Tap(Locator(by=LocatorStrategy.ID, value="ok"), name="tap_ok"))
        .step(Tap(Locator(by=LocatorStrategy.ID, value="missing"), name="tap_missing"))
    )
    with pytest.raises(ElementNotFoundError):
        scenario.run(ctx)

    bus.publish(
        TestFinished(
            run_id=run_id,
            test_id=test_id,
            nodeid=test_id,
            status="failed",
            verdict="test",
            error_type="ElementNotFoundError",
            error_message="missing",
            tags={
                "driver_alive": "true",
                "app_scene": "MockScene",
                "feature_id": "x",
            },
        )
    )

    dp = store.death_point(test_id)
    assert dp["last_started_step"] is not None
    assert dp["last_started_step"]["name"].endswith("tap_missing")
    # Failed step still gets StepFinished(status=failed) — that is the last finished.
    assert dp["last_finished_step"]["name"].endswith("tap_missing")
    assert dp["last_finished_step"]["status"] == "failed"
    assert dp["driver_health"]["driver_alive"] == "true"
    assert dp["test"]["feature_id"] == "x"
    store.close()


def test_quarantine_audit_catches_seeded_limbo(tmp_path: Path) -> None:
    ledger_path = tmp_path / "quarantine.yaml"
    ledger = QuarantineLedger(ledger_path)
    ledger.add(
        "seeded_limbo::test_missing_marker",
        reason="seed",
        owner="ci",
        exit_criteria="n/a",
        feature="demo",
    )
    ledger.save()
    report = ledger.audit(set())
    assert report.ok is False
    assert "seeded_limbo::test_missing_marker" in report.ledger_only


def test_demo_quarantine_ledger_in_sync_with_marker() -> None:
    ledger = QuarantineLedger.load(DEMO / "quarantine.yaml")
    marked = {_norm(m) for m in collect_quarantined_nodeids([str(DEMO)], rootdir=ROOT)}
    ledger_ids = {_norm(t) for t in ledger.test_ids()}
    report = ledger.audit(marked)
    # Re-audit with normalized sets if Windows path separators differ.
    if not report.ok:
        from questline.authoring.quarantine import AuditReport

        report = AuditReport(
            ledger_only=sorted(ledger_ids - marked),
            marker_only=sorted(marked - ledger_ids),
        )
    assert report.ok, report.summary() + f"\nmarked={marked}\nledger={ledger_ids}"
