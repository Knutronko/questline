"""GitHubIssuesReporter — test-verdict only, dedupe, no infra filing."""

from __future__ import annotations

import pytest

from questline.core.config import Settings
from questline.core.errors import AuthoringError
from questline.reporters.github_issues import (
    FakeGitHubIssuesTransport,
    GitHubIssuesReporter,
    failure_signature,
)
from questline.reporters.port import RunSummary, TestResultSummary


def _settings(**kwargs: object) -> Settings:
    base = {
        "profile": "ci",
        "github_token": "ghp_fake",
        "github_repo": "acme/sandbox",
        "github_issues_auto_close": True,
    }
    base.update(kwargs)
    return Settings.model_validate(base)


def _summary(*tests: TestResultSummary, status: str = "failed") -> RunSummary:
    failed = sum(1 for t in tests if t.status in {"failed", "error"})
    infra = sum(1 for t in tests if t.verdict == "infra")
    test_v = sum(1 for t in tests if t.verdict == "test")
    return RunSummary(
        run_id="r1",
        profile="ci",
        status=status,
        failed=failed,
        infra_failures=infra,
        test_failures=test_v,
        tests=tests,
    )


def test_infra_failure_files_nothing() -> None:
    fake = FakeGitHubIssuesTransport()
    reporter = GitHubIssuesReporter(settings=_settings(), transport=fake)
    reporter.finalize(
        _summary(
            TestResultSummary(
                test_id="t-infra",
                nodeid="tests/test_x.py::test_session",
                status="failed",
                verdict="infra",
                error_type="SessionLostError",
                error_message="connection reset",
            )
        )
    )
    assert fake.issues == []
    assert fake.comments == []


def test_test_failure_files_issue_and_dedupes_on_rerun() -> None:
    fake = FakeGitHubIssuesTransport()
    reporter = GitHubIssuesReporter(settings=_settings(), transport=fake)
    failure = TestResultSummary(
        test_id="t-uuid-1",
        nodeid="tests/test_x.py::test_assert",
        status="failed",
        verdict="test",
        error_type="AssertionFailedError",
        error_message="expected 1 got 2",
        death_step_name="check_score",
    )
    reporter.finalize(_summary(failure))
    assert len(fake.issues) == 1
    body = fake.issues[0]["body"]
    assert "| verdict | test |" in body
    assert "questline:signature=" in body
    assert "{signature}" not in body
    assert r"D:\secrets" not in body

    # Rerun with new test_id UUID but same nodeid + error → comment, no duplicate.
    failure2 = TestResultSummary(
        test_id="t-uuid-2",
        nodeid="tests/test_x.py::test_assert",
        status="failed",
        verdict="test",
        error_type="AssertionFailedError",
        error_message="expected 1 got 2",
        death_step_name="check_score",
    )
    reporter.finalize(_summary(failure2))
    assert len(fake.issues) == 1
    assert len(fake.comments) == 1
    assert "Rerun" in fake.comments[0]["body"]


def test_signature_stable_across_volatile_numbers() -> None:
    a = failure_signature(
        test_id="tests/a.py::t",
        error_type="Error",
        error_message="timeout after 12345 ms at 0xDEAD",
    )
    b = failure_signature(
        test_id="tests/a.py::t",
        error_type="Error",
        error_message="timeout after 99999 ms at 0xBEEF",
    )
    assert a == b


def test_auto_close_on_green() -> None:
    fake = FakeGitHubIssuesTransport()
    reporter = GitHubIssuesReporter(settings=_settings(), transport=fake)
    failure = TestResultSummary(
        test_id="t1",
        nodeid="tests/test_x.py::test_flaky",
        status="failed",
        verdict="test",
        error_type="AssertionFailedError",
        error_message="boom",
    )
    reporter.finalize(_summary(failure))
    assert fake.issues[0]["state"] == "open"

    reporter.finalize(_summary(status="passed"))
    assert fake.issues[0]["state"] == "closed"
    assert fake.closed == [1]


def test_github_requires_token_and_repo() -> None:
    with pytest.raises(AuthoringError, match="QUESTLINE_GITHUB_TOKEN"):
        GitHubIssuesReporter(
            settings=Settings(profile="ci", github_repo="a/b"),
            transport=None,
        )
    with pytest.raises(AuthoringError, match="github_repo"):
        GitHubIssuesReporter(
            settings=Settings(profile="ci", github_token="x"),
            transport=None,
        )
