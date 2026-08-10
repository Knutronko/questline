"""TestRailReporter stub — port-conformant, not implemented in v0.1."""

from __future__ import annotations

from questline.core.events import Event
from questline.reporters.port import RunSummary

_MSG = (
    "TestRailReporter is a documented stub (phase-07). Intended mapping: push a "
    "TestRail run result set from RunSummary (case ids via markers/feature_id); "
    "verdicts map to TestRail statuses without inventing green. See docs/reporting.md."
)


class TestRailReporter:
    """TestRail result-push adapter stub (not implemented)."""

    def on_event(self, event: Event) -> None:
        raise NotImplementedError(_MSG)

    def finalize(self, run_summary: RunSummary) -> None:
        raise NotImplementedError(_MSG)
