"""Reporter crash isolation — one bad reporter must not affect others or the run."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from questline.core.events import (
    EventBus,
    RunFinished,
    RunStarted,
    StepStarted,
    TestFinished,
    TestStarted,
)
from questline.core.store import RunStore
from questline.reporters.console import ConsoleReporter
from questline.reporters.html import HtmlReporter
from questline.reporters.port import RunSummary
from questline.reporters.registry import finalize_all
from questline.reporters.summary import build_run_summary


class ExplodingReporter:
    def on_event(self, event: object) -> None:
        raise RuntimeError("reporter exploded on purpose")

    def finalize(self, run_summary: RunSummary) -> None:
        raise RuntimeError("finalize exploded on purpose")


def test_console_tracks_steps_and_failures() -> None:
    reporter = ConsoleReporter()
    reporter.on_event(RunStarted(run_id="r1", profile="ci"))
    reporter.on_event(TestStarted(run_id="r1", test_id="t1", nodeid="a::fail"))
    reporter.on_event(StepStarted(run_id="r1", test_id="t1", step_id="s1", name="tap"))
    reporter.on_event(
        TestFinished(
            run_id="r1",
            test_id="t1",
            nodeid="a::fail",
            status="failed",
            verdict="infra",
        )
    )
    reporter.on_event(
        TestFinished(
            run_id="r1",
            test_id="t2",
            nodeid="a::skip",
            status="skipped",
        )
    )
    reporter.on_event(RunFinished(run_id="r1", status="failed", duration_s=0.2))
    reporter.finalize(RunSummary(run_id="r1", profile="ci", status="failed"))
    assert reporter._failed == 1
    assert reporter._infra == 1
    assert reporter._skipped == 1


def test_reporter_crash_isolation_on_event_and_finalize(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "artifacts")
    store.attach(bus)

    bad = ExplodingReporter()
    html = HtmlReporter(output_dir=tmp_path / "artifacts")
    console = ConsoleReporter()
    reporters = [bad, html, console]
    for r in reporters:
        bus.subscribe(r.on_event)

    with caplog.at_level(logging.ERROR, logger="questline.events"):
        bus.publish(RunStarted(run_id="r1", profile="ci"))
        bus.publish(
            TestStarted(
                run_id="r1",
                test_id="t1",
                nodeid="tests/test_x.py::test_a",
            )
        )
        bus.publish(
            TestFinished(
                run_id="r1",
                test_id="t1",
                nodeid="tests/test_x.py::test_a",
                status="passed",
            )
        )
        bus.publish(RunFinished(run_id="r1", status="passed", duration_s=0.5))

    assert store.get_run("r1") is not None
    assert store.list_tests("r1")
    assert any("subscriber" in r.message for r in caplog.records)

    summary = build_run_summary(store, "r1", profile="ci")
    with caplog.at_level(logging.ERROR, logger="questline.reporters"):
        finalize_all(reporters, summary)

    assert html.last_path is not None
    assert html.last_path.is_file()
    assert any("finalize failed" in r.message for r in caplog.records)

    store.close()
