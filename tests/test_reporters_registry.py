"""Reporter registry, HTML artifact, stubs."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.config import Settings
from questline.core.errors import AuthoringError
from questline.core.events import (
    EventBus,
    RunFinished,
    RunStarted,
    StepStarted,
    TestFinished,
    TestStarted,
)
from questline.core.store import RunStore
from questline.reporters.github_issues import FakeGitHubIssuesTransport
from questline.reporters.html import HtmlReporter
from questline.reporters.port import RunSummary
from questline.reporters.registry import build_reporters
from questline.reporters.slack import FakeSlackTransport
from questline.reporters.summary import build_run_summary


def test_build_reporters_console_html(tmp_path: Path) -> None:
    settings = Settings(
        profile="ci",
        reporters=["console", "html"],
        store_dir=tmp_path / ".questline",
    )
    reps = build_reporters(settings)
    assert len(reps) == 2


def test_build_reporters_unknown_raises() -> None:
    with pytest.raises(AuthoringError, match="not available"):
        build_reporters(Settings(profile="ci", reporters=["telepathy"]))


def test_build_slack_and_github_with_fakes(tmp_path: Path) -> None:
    settings = Settings(
        profile="ci",
        reporters=["slack", "github_issues"],
        slack_token="x",
        github_token="y",
        github_repo="acme/sandbox",
        store_dir=tmp_path / ".questline",
    )
    store = RunStore(tmp_path / "db.sqlite")
    reps = build_reporters(
        settings,
        store=store,
        slack_transport=FakeSlackTransport(),
        github_transport=FakeGitHubIssuesTransport(),
    )
    assert len(reps) == 2
    store.close()


def test_html_report_written(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "art")
    store.attach(bus)
    html = HtmlReporter(output_dir=tmp_path / "art")
    bus.subscribe(html.on_event)

    bus.publish(RunStarted(run_id="r1", profile="ci"))
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="t1",
            nodeid="tests/a.py::test_ok",
            status="passed",
            duration_s=0.01,
        )
    )
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="t2",
            nodeid="tests/a.py::test_bad",
            status="failed",
            verdict="test",
            error_type="AssertionFailedError",
            error_message="nope",
        )
    )
    bus.publish(RunFinished(run_id="r1", status="failed", duration_s=1.0))
    summary = build_run_summary(store, "r1", profile="ci", driver="mock")
    html.finalize(summary)
    assert html.last_path is not None
    text = html.last_path.read_text(encoding="utf-8")
    assert "test_ok" in text
    assert "test_bad" in text
    assert "verdict-test" in text
    store.close()


def test_build_stub_reporters() -> None:
    settings = Settings(profile="ci", reporters=["notion", "jira", "testrail"])
    reps = build_reporters(settings)
    assert len(reps) == 3
    for r in reps:
        with pytest.raises(NotImplementedError):
            r.finalize(RunSummary(run_id="r", profile="ci", status="passed"))


def test_summary_verdict_buckets_and_death_step(tmp_path: Path) -> None:
    bus = EventBus()
    store = RunStore(tmp_path / "store.db")
    store.attach(bus)
    bus.publish(RunStarted(run_id="r1", profile="ci"))
    for tid, nodeid, status, verdict in (
        ("t1", "a::ok", "passed", None),
        ("t2", "a::infra", "failed", "infra"),
        ("t3", "a::test", "failed", "test"),
        ("t4", "a::auth", "failed", "authoring"),
        ("t5", "a::unk", "failed", "unknown"),
        ("t6", "a::skip", "skipped", None),
        ("t7", "a::err", "error", None),
    ):
        bus.publish(TestStarted(run_id="r1", test_id=tid, nodeid=nodeid))
        if tid == "t3":
            bus.publish(
                StepStarted(run_id="r1", test_id=tid, step_id="s1", name="tap_play")
            )
        bus.publish(
            TestFinished(
                run_id="r1",
                test_id=tid,
                nodeid=nodeid,
                status=status,
                verdict=verdict,
                error_type="E" if status in {"failed", "error"} else None,
                error_message="m" if status in {"failed", "error"} else None,
            )
        )
    bus.publish(RunFinished(run_id="r1", status="failed", duration_s=2.0))
    summary = build_run_summary(store, "r1", profile="ci", driver="mock", device="local")
    assert summary.passed == 1
    assert summary.skipped == 1
    assert summary.error == 1
    assert summary.infra_failures == 1
    assert summary.test_failures == 1
    assert summary.authoring_failures == 1
    assert summary.unknown_failures == 2  # unknown + error without verdict
    assert summary.total == 7
    death = next(t for t in summary.tests if t.test_id == "t3")
    assert death.death_step_name == "tap_play"
    assert summary.failed_tests(verdict="test")[0].nodeid == "a::test"
    store.close()
