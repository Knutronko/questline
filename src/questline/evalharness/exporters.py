"""Optional DeepEval / Langfuse shaped dumps. Stubs — not live exporters."""

from __future__ import annotations

from typing import Any


def to_deepeval(run: dict[str, Any]) -> dict[str, Any]:
    """Map an eval run to a DeepEval-like test-case list (offline stub)."""
    cases = run.get("cases") or (run.get("metrics") and []) or []
    if isinstance(run.get("cases"), list):
        cases = run["cases"]
    test_cases = []
    for row in cases:
        test_cases.append(
            {
                "name": row.get("id"),
                "success": bool(row.get("diagnosis_ok")),
                "metrics": {
                    "diagnosis_ok": row.get("diagnosis_ok"),
                    "fix_ok": row.get("fix_ok"),
                    "false_green": row.get("false_green"),
                },
                "actual_output": row.get("cause_actual"),
                "expected_output": row.get("cause_expected"),
            }
        )
    return {
        "format": "deepeval-stub",
        "eval_id": run.get("id"),
        "test_cases": test_cases,
        "note": "Offline mapping only. Does not call DeepEval.",
    }


def to_langfuse(run: dict[str, Any]) -> dict[str, Any]:
    """Map an eval run to a Langfuse-like trace list (offline stub)."""
    cases = run.get("cases") if isinstance(run.get("cases"), list) else []
    traces = []
    for row in cases:
        traces.append(
            {
                "id": row.get("id"),
                "name": "questline.eval",
                "metadata": {
                    "failure_class": row.get("failure_class"),
                    "false_green": row.get("false_green"),
                },
                "output": row.get("cause_actual"),
                "expected": row.get("cause_expected"),
            }
        )
    return {
        "format": "langfuse-stub",
        "eval_id": run.get("id"),
        "traces": traces,
        "note": "Offline mapping only. Does not call Langfuse.",
    }
