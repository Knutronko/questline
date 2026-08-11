"""Reporter allow-list factory (mirrors driver registration style)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from questline.core.config import Settings
from questline.core.errors import AuthoringError
from questline.core.store import RunStore
from questline.reporters.port import ReporterPort

logger = logging.getLogger("questline.reporters")

# Concrete adapters only — stubs are constructible but raise on use.
KNOWN_REPORTERS = frozenset(
    {
        "console",
        "html",
        "slack",
        "github_issues",
        "github",
        "notion",
        "jira",
        "testrail",
    }
)
_KNOWN = KNOWN_REPORTERS  # backward-compatible alias


def build_reporters(
    settings: Settings,
    *,
    store: RunStore | None = None,
    slack_transport: Any = None,
    github_transport: Any = None,
) -> list[ReporterPort]:
    """Instantiate reporters named in ``settings.reporters``.

    Unknown names raise AuthoringError (actionable). Optional *transport*
    kwargs inject fakes for CI.
    """
    names = [n.strip().lower() for n in settings.reporters if n and n.strip()]
    if not names:
        return []

    out: list[ReporterPort] = []
    for name in names:
        if name not in _KNOWN:
            available = ", ".join(sorted(_KNOWN))
            raise AuthoringError(
                f"Reporter '{name}' is not available. "
                f"Known reporters: {available}. "
                f'Fix reporters = [...] in the profile or QUESTLINE_REPORTERS.'
            )
        out.append(
            _build_one(
                name,
                settings,
                store=store,
                slack_transport=slack_transport,
                github_transport=github_transport,
            )
        )
    return out


def finalize_all(reporters: Sequence[ReporterPort], run_summary: Any) -> None:
    """Call finalize on each reporter; isolate exceptions (bus covers on_event only)."""
    for reporter in reporters:
        try:
            reporter.finalize(run_summary)
        except Exception:
            logger.exception(
                "reporter %r finalize failed (isolated; other reporters continue)",
                reporter,
            )


def _build_one(
    name: str,
    settings: Settings,
    *,
    store: RunStore | None,
    slack_transport: Any,
    github_transport: Any,
) -> ReporterPort:
    if name == "console":
        from questline.reporters.console import ConsoleReporter

        return ConsoleReporter()

    if name == "html":
        from questline.reporters.html import HtmlReporter

        artifacts = settings.artifacts_dir
        return HtmlReporter(output_dir=artifacts)

    if name == "slack":
        from questline.reporters.slack import SlackReporter

        return SlackReporter(
            settings=settings,
            transport=slack_transport,
        )

    if name in {"github_issues", "github"}:
        from questline.reporters.github_issues import GitHubIssuesReporter

        return GitHubIssuesReporter(
            settings=settings,
            store=store,
            transport=github_transport,
        )

    if name == "notion":
        from questline.reporters.notion import NotionReporter

        return NotionReporter()

    if name == "jira":
        from questline.reporters.jira import JiraReporter

        return JiraReporter()

    if name == "testrail":
        from questline.reporters.testrail import TestRailReporter

        return TestRailReporter()

    raise AuthoringError(f"Reporter '{name}' is not available.")  # pragma: no cover
