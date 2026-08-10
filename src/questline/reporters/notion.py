"""NotionReporter stub — port-conformant, not implemented in v0.1."""

from __future__ import annotations

from questline.core.events import Event
from questline.reporters.port import RunSummary

_MSG = (
    "NotionReporter is a documented stub (phase-07). Intended mapping: one Notion "
    "database row per run (profile, status, duration, verdict counts) plus child "
    "pages per failed test. Implement in a later wave with questline[notion]. "
    "See docs/reporting.md."
)


class NotionReporter:
    """2nd-wave Notion dashboard adapter (not implemented)."""

    def on_event(self, event: Event) -> None:
        raise NotImplementedError(_MSG)

    def finalize(self, run_summary: RunSummary) -> None:
        raise NotImplementedError(_MSG)
