"""JiraReporter stub — port-conformant, not implemented in v0.1."""

from __future__ import annotations

from questline.core.events import Event
from questline.reporters.port import RunSummary

_MSG = (
    "JiraReporter is a documented stub (phase-07). Intended mapping: create/update "
    "Jira issues for verdict=test failures only (same signature-dedupe policy as "
    "GitHubIssuesReporter); never file infra. See docs/reporting.md."
)


class JiraReporter:
    """Jira issue adapter stub (not implemented)."""

    def on_event(self, event: Event) -> None:
        raise NotImplementedError(_MSG)

    def finalize(self, run_summary: RunSummary) -> None:
        raise NotImplementedError(_MSG)
