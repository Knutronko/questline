"""Versioned structured output for phase-12 test agents."""

from __future__ import annotations

import json
import re
from typing import Any

SCHEMA_VERSION = "1"
VERDICTS = frozenset({"diagnosed", "fixed", "inconclusive", "passed"})
CAUSES = frozenset({"test-bug", "game-bug", "infra", "flaky", "unknown"})


def extract_json(text: str) -> dict[str, Any] | None:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        stripped = (text or "").strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            candidate = stripped
    if candidate is None:
        match = re.search(r"\{.*\}", text or "", re.DOTALL)
        candidate = match.group(0) if match else None
    if not candidate:
        return None
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def parse_agent_output(text: str) -> dict[str, Any]:
    """Parse model text into the phase-12 contract. Unknown fields are dropped."""
    blob = extract_json(text) or {}
    verdict = str(blob.get("verdict") or "").strip().lower()
    if verdict not in VERDICTS:
        verdict = "inconclusive"
    cause = str(blob.get("cause") or "").strip().lower()
    if cause not in CAUSES:
        cause = "unknown"
    evidence_raw = blob.get("evidence")
    evidence: list[Any] = list(evidence_raw) if isinstance(evidence_raw, list) else []
    summary = str(blob.get("summary") or text or "").strip()
    clusters = blob.get("clusters")
    fix_class = str(blob.get("fix_class") or "").strip().lower() or None
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "cause": cause,
        "evidence": evidence,
        "summary": summary,
        "clusters": clusters if isinstance(clusters, list) else [],
        "patch": blob.get("patch"),
        "suggestion": blob.get("suggestion") if isinstance(blob.get("suggestion"), dict) else None,
        "fix_class": fix_class,
    }
