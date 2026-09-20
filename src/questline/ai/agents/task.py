"""Persisted agent-task record (store index + artifact)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from questline.ai.agents.schema import SCHEMA_VERSION


@dataclass
class AgentTask:
    """One triage / diagnose / fix / heal task. Persisted incrementally."""

    id: str
    kind: str
    run_id: str | None = None
    test_id: str | None = None
    status: str = "running"
    verdict: str | None = None
    cause: str | None = None
    evidence: list[Any] = field(default_factory=list)
    summary: str = ""
    clusters: list[dict[str, Any]] = field(default_factory=list)
    patch: str | None = None
    suggestion: dict[str, Any] | None = None
    tool_log: list[dict[str, Any]] = field(default_factory=list)
    agent_claim: dict[str, Any] | None = None
    prompt_version: str = "v1"
    purpose_tag: str = ""
    artifact_path: str | None = None
    created_at: str | None = None
    pending: str | None = None
    schema_version: str = SCHEMA_VERSION
    gate: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "run_id": self.run_id,
            "test_id": self.test_id,
            "status": self.status,
            "verdict": self.verdict,
            "cause": self.cause,
            "evidence": list(self.evidence),
            "summary": self.summary,
            "clusters": list(self.clusters),
            "patch": self.patch,
            "suggestion": self.suggestion,
            "tool_log": list(self.tool_log),
            "agent_claim": self.agent_claim,
            "prompt_version": self.prompt_version,
            "purpose_tag": self.purpose_tag,
            "artifact_path": self.artifact_path,
            "created_at": self.created_at,
            "pending": self.pending,
            "schema_version": self.schema_version,
            "gate": self.gate,
        }
