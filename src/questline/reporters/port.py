"""ReporterPort protocol and run-summary types (architecture §3.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from questline.core.events import Event


@dataclass(frozen=True, slots=True)
class TestResultSummary:
    """Allow-listed per-test facts for exporters (never raw store rows)."""

    __test__ = False

    test_id: str
    nodeid: str
    status: str
    verdict: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    duration_s: float | None = None
    death_step_name: str | None = None
    feature_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Sealed view of a finished run for ``finalize`` — built from the store."""

    run_id: str
    profile: str
    status: str
    duration_s: float | None = None
    driver: str | None = None
    device: str | None = None
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    error: int = 0
    infra_failures: int = 0
    test_failures: int = 0
    authoring_failures: int = 0
    unknown_failures: int = 0
    tests: tuple[TestResultSummary, ...] = ()
    html_path: str | None = None
    extras: dict[str, str] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.error

    def failed_tests(self, *, verdict: str | None = None) -> list[TestResultSummary]:
        out = [t for t in self.tests if t.status in {"failed", "error"}]
        if verdict is not None:
            out = [t for t in out if t.verdict == verdict]
        return out


@runtime_checkable
class ReporterPort(Protocol):
    """Event-bus subscriber that may also seal a run via ``finalize``."""

    def on_event(self, event: Event) -> None:
        """Handle a single bus event. Exceptions are isolated by EventBus."""
        ...

    def finalize(self, run_summary: RunSummary) -> None:
        """Called after RunFinished is persisted. Must not raise across reporters
        (plugin isolates); adapters should still prefer raising so isolation logs."""
        ...
