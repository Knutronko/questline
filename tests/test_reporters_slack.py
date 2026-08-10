"""SlackReporter unit tests against FakeSlackTransport (no live Slack in CI)."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.config import Settings
from questline.core.errors import AuthoringError
from questline.core.events import RunStarted
from questline.reporters.port import RunSummary, TestResultSummary
from questline.reporters.slack import FakeSlackTransport, SlackReporter


def _settings(**kwargs: object) -> Settings:
    base = {
        "profile": "ci",
        "driver": "mock",
        "device": "local",
        "slack_channel": "C123",
        "slack_token": "xoxb-fake",
    }
    base.update(kwargs)
    return Settings.model_validate(base)


def test_slack_start_finish_and_failure_thread() -> None:
    fake = FakeSlackTransport()
    reporter = SlackReporter(settings=_settings(), transport=fake)

    reporter.on_event(RunStarted(run_id="r1", profile="ci"))
    assert len(fake.messages) == 1
    assert "profile=ci" in fake.messages[0]["text"]
    assert r"D:\secrets" not in fake.messages[0]["text"]

    summary = RunSummary(
        run_id="r1",
        profile="ci",
        status="failed",
        duration_s=1.25,
        driver="mock",
        device="local",
        passed=0,
        failed=1,
        test_failures=1,
        tests=(
            TestResultSummary(
                test_id="t1",
                nodeid="tests/test_x.py::test_boom",
                status="failed",
                verdict="test",
                error_type="AssertionFailedError",
                error_message="expected True",
                death_step_name="tap_play",
            ),
        ),
    )
    reporter.finalize(summary)
    assert len(fake.updates) == 1
    assert "status=failed" in fake.updates[0]["text"]
    assert "infra=0" in fake.updates[0]["text"]
    assert len(fake.replies) == 1
    assert "test_boom" in fake.replies[0]["text"]
    assert "tap_play" in fake.replies[0]["text"]


def test_slack_webhook_mode_posts_without_thread() -> None:
    fake = FakeSlackTransport()
    settings = _settings(slack_token=None, slack_webhook="https://hooks.example/x")
    reporter = SlackReporter(settings=settings, transport=fake)
    reporter.on_event(RunStarted(run_id="r2", profile="ci"))
    reporter.finalize(
        RunSummary(run_id="r2", profile="ci", status="passed", passed=1, duration_s=0.1)
    )
    assert len(fake.webhooks) >= 2
    assert fake.messages == []


def test_slack_requires_secret(tmp_path: Path) -> None:
    _ = tmp_path
    with pytest.raises(AuthoringError, match="QUESTLINE_SLACK"):
        SlackReporter(settings=Settings(profile="ci"), transport=None)


def test_slack_allowlist_in_templates(tmp_path: Path) -> None:
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "start.txt").write_text(
        "ok={{run_id}} leak={{artifact_path}} env={{HOME}}\n",
        encoding="utf-8",
    )
    (templates / "finish.txt").write_text("done={{status}}\n", encoding="utf-8")
    (templates / "failure.txt").write_text("fail={{nodeid}}\n", encoding="utf-8")
    fake = FakeSlackTransport()
    reporter = SlackReporter(
        settings=_settings(),
        transport=fake,
        templates_dir=templates,
    )
    reporter.on_event(RunStarted(run_id="r3", profile="ci"))
    text = fake.messages[0]["text"]
    assert "ok=r3" in text
    assert "leak=" in text
    assert "token.dump" not in text
    assert "Users" not in text
