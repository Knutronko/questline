"""Golden-case and eval-run records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FAILURE_CLASSES = frozenset({"locator", "assertion", "infra", "timing", "green"})


@dataclass
class GoldenCase:
    id: str
    failure_class: str
    cause: str
    expected_fix_class: str
    agent: str = "maintainer"
    mode: str = "diagnose"
    score_fix: bool = False
    error_type: str = "AssertionError"
    error_message: str = "golden"
    store_verdict: str = "test"
    summary: str = ""
    reply: dict[str, Any] = field(default_factory=dict)
    sabotage_gate: bool = False
    gate_green: bool = False
    actually_green: bool | None = None
    setup: str = ""

    def truth_green(self) -> bool:
        if self.sabotage_gate:
            return False
        if self.actually_green is not None:
            return bool(self.actually_green)
        return bool(self.gate_green)


@dataclass
class EvalRun:
    id: str
    agent: str
    provider: str
    prompt_version: str
    status: str = "ok"
    diagnosis_accuracy: float | None = None
    fix_correctness: float | None = None
    false_green_rate: float | None = None
    iterations_avg: float | None = None
    cost_usd: float = 0.0
    case_count: int = 0
    cases: list[dict[str, Any]] = field(default_factory=list)
    artifact_path: str | None = None
    created_at: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def metrics_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_accuracy": self.diagnosis_accuracy,
            "fix_correctness": self.fix_correctness,
            "false_green_rate": self.false_green_rate,
            "iterations_avg": self.iterations_avg,
            "cost_usd": self.cost_usd,
            "case_count": self.case_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent": self.agent,
            "provider": self.provider,
            "prompt_version": self.prompt_version,
            "status": self.status,
            "metrics": self.metrics_dict(),
            "cases": list(self.cases),
            "artifact_path": self.artifact_path,
            "created_at": self.created_at,
            "meta": dict(self.meta),
        }
