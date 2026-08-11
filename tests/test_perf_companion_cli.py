"""Companion collector + CLI perf report."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from questline.cli import app
from questline.core.events import EventBus, PerfSample, RunStarted
from questline.core.store import RunStore
from questline.drivers.port import GameHook
from questline.drivers.wire.fake import FakeWireDriverHarness
from questline.perf.companion import companion_collector_from_driver


def test_companion_collector_via_fake_wire() -> None:
    harness = FakeWireDriverHarness()
    driver = harness()
    from questline.drivers.port import ConnectionTarget

    driver.connect(ConnectionTarget(host="127.0.0.1", port=13000, platform="editor"))
    collector = companion_collector_from_driver(driver)
    sample = dict(collector.collect())
    assert sample["fps"] == 60.0
    assert sample["allocated_mb"] == 128.0
    assert sample["draw_calls"] == 42.0
    # Direct hook also works.
    raw = driver.call_game_method(GameHook("GetPerfSample"))
    assert raw["fps"] == 60.0
    driver.disconnect()


def test_perf_report_cli(tmp_path: Path) -> None:
    db = tmp_path / "store.db"
    bus = EventBus()
    store = RunStore(db, artifacts_dir=tmp_path / "artifacts")
    store.attach(bus)
    bus.publish(RunStarted(run_id="run-cli", profile="ci"))
    for v in (50.0, 60.0, 70.0):
        bus.publish(PerfSample(run_id="run-cli", test_id="t", metric="fps", value=v))
    store.close()

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["perf", "report", "run-cli", "--store", str(db)],
    )
    assert result.exit_code == 0, result.output
    assert "fps" in result.output
    assert "60.000" in result.output or "60.0" in result.output

    html = runner.invoke(
        app,
        [
            "perf",
            "report",
            "run-cli",
            "--store",
            str(db),
            "--format",
            "html",
            "--output",
            str(tmp_path / "out.html"),
        ],
    )
    assert html.exit_code == 0, html.output
    assert (tmp_path / "out.html").is_file()
    assert "Questline perf report" in (tmp_path / "out.html").read_text(encoding="utf-8")
