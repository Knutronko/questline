"""AI implications report — stub until phase-11 LLMPort."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from questline.lens.diff import DiffReport


@dataclass(frozen=True, slots=True)
class ImplicationsReport:
    """Labeled *model reasoning* placeholder (never a pass/fail verdict)."""

    status: str
    framing: str
    summary: str
    pending: str | None = None
    diff_entry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "framing": self.framing,
            "summary": self.summary,
            "pending": self.pending,
            "diff_entry_count": self.diff_entry_count,
        }


def implications_stub(report: DiffReport) -> ImplicationsReport:
    """Return an explicit deferred report — no live LLM in FP-G1."""
    return ImplicationsReport(
        status="pending",
        framing="model reasoning",
        summary=(
            "AI implications report is deferred until phase-11 (LLMPort). "
            f"Diff has {len(report.entries)} typed entries "
            f"({report.version_a} → {report.version_b}); "
            "use measured telemetry (FP-G2/G3) before trusting narrative prioritization."
        ),
        pending="phase-11",
        diff_entry_count=len(report.entries),
    )
