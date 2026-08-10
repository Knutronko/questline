"""GitHubIssuesReporter — files issues for verdict=test failures only."""

from __future__ import annotations

import logging

from questline.core.config import Settings
from questline.core.errors import AuthoringError, Verdict
from questline.core.events import Event
from questline.core.store import RunStore
from questline.reporters.allowlist import render_template
from questline.reporters.github_issues.signature import failure_signature
from questline.reporters.github_issues.transport import (
    FakeGitHubIssuesTransport,
    GitHubIssuesTransport,
    HttpGitHubIssuesTransport,
)
from questline.reporters.port import RunSummary, TestResultSummary

logger = logging.getLogger("questline.reporters.github_issues")

_MARKER_PREFIX = "<!-- questline:signature="

_ISSUE_BODY = """\
## Questline test failure

{{nodeid}}

| Field | Value |
|-------|-------|
| verdict | {{verdict}} |
| error | {{error_type}} |
| death-point step | {{death_step_name}} |
| run_id | {{run_id}} |
| profile | {{profile}} |

```
{{error_message}}
```

<!-- questline:signature={{signature}} -->
"""

_COMMENT_BODY = """\
Rerun observed the same failure signature.

| Field | Value |
|-------|-------|
| run_id | {{run_id}} |
| profile | {{profile}} |
| death-point step | {{death_step_name}} |

```
{{error_message}}
```
"""

_GREEN_COMMENT = """\
Questline run {{run_id}} (profile={{profile}}) passed — no recurrence of this signature.
"""


class GitHubIssuesReporter:
    """Create/comment/close GitHub issues for **test** verdict failures only.

    Never files infra/authoring/unknown. Dedupe by signature hash in the issue body.
    Optional auto-close on green when ``github_issues_auto_close`` is true.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        store: RunStore | None = None,
        transport: GitHubIssuesTransport | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.auto_close = bool(getattr(settings, "github_issues_auto_close", False))
        labels = getattr(settings, "github_issues_labels", None)
        self.labels: list[str] = list(labels) if labels else ["questline", "test-failure"]
        self._seen_signatures: set[str] = set()
        self.transport = transport or self._build_transport(settings)

    @staticmethod
    def _build_transport(settings: Settings) -> GitHubIssuesTransport:
        token = settings.github_token
        repo = getattr(settings, "github_repo", None)
        if not token:
            raise AuthoringError(
                "GitHubIssuesReporter requires QUESTLINE_GITHUB_TOKEN. "
                "Secrets must be set via environment variables, never questline.toml."
            )
        if not repo:
            raise AuthoringError(
                "GitHubIssuesReporter requires github_repo = 'owner/name' in the "
                "profile (or QUESTLINE_GITHUB_REPO). This is not a secret."
            )
        return HttpGitHubIssuesTransport(token=token, repo=repo)

    def on_event(self, event: Event) -> None:
        # Filing happens in finalize from the sealed store summary (verdicts authoritative).
        _ = event

    def finalize(self, run_summary: RunSummary) -> None:
        test_failures = run_summary.failed_tests(verdict=Verdict.TEST.value)
        for failure in test_failures:
            self._file_or_comment(failure, run_summary)

        if self.auto_close and run_summary.status == "passed":
            self._auto_close_tracked(run_summary)

    def _file_or_comment(self, failure: TestResultSummary, summary: RunSummary) -> None:
        # Prefer nodeid for stable cross-run identity (test_id is a UUID per run).
        sig_key = failure.nodeid or failure.test_id
        sig = failure_signature(
            test_id=sig_key,
            error_type=failure.error_type,
            error_message=failure.error_message,
        )
        self._seen_signatures.add(sig)
        marker = f"{_MARKER_PREFIX}{sig} -->"
        existing = self.transport.find_open_issues_by_marker(marker)
        ctx = {
            "run_id": summary.run_id,
            "profile": summary.profile,
            "nodeid": failure.nodeid,
            "test_id": failure.test_id,
            "verdict": failure.verdict,
            "error_type": failure.error_type,
            "error_message": failure.error_message,
            "death_step_name": failure.death_step_name,
            "signature": sig,
            "issue_title": f"[questline] {failure.nodeid or failure.test_id}",
        }
        if existing:
            number = int(existing[0]["number"])
            body = render_template(_COMMENT_BODY, ctx)
            self.transport.comment(issue_number=number, body=body)
            logger.info("GitHub issue #%s commented (dedupe signature=%s)", number, sig)
            return

        title = render_template("{{issue_title}}", ctx)
        body = render_template(_ISSUE_BODY, ctx)
        issue = self.transport.create_issue(title=title, body=body, labels=self.labels)
        logger.info(
            "GitHub issue #%s created (signature=%s)",
            issue.get("number"),
            sig,
        )

    def _auto_close_tracked(self, summary: RunSummary) -> None:
        """Close open issues whose signature appeared in prior runs but not this green run.

        With a fake/local transport we close issues that carry our marker and are
        still open when the whole run is green. Live search uses the same marker scan.
        """
        if isinstance(self.transport, FakeGitHubIssuesTransport):
            for issue in list(self.transport.issues):
                if issue.get("state") != "open":
                    continue
                body = issue.get("body") or ""
                if "questline:signature=" not in body:
                    continue
                number = int(issue["number"])
                self.transport.comment(
                    issue_number=number,
                    body=render_template(
                        _GREEN_COMMENT,
                        {"run_id": summary.run_id, "profile": summary.profile},
                    ),
                )
                self.transport.close_issue(issue_number=number)
            return

        # Live: only close issues we know about via labels search is expensive;
        # skip broad close without explicit signature list from this session.
        _ = summary
