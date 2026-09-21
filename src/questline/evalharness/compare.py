"""Compare two eval runs (model A vs B, prompt v1 vs v2)."""

from __future__ import annotations

from typing import Any

_KEYS = (
    "diagnosis_accuracy",
    "fix_correctness",
    "false_green_rate",
    "iterations_avg",
    "cost_usd",
)


def compare_eval_runs(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Delta is B − A. Lower is better for false_green_rate / cost / iterations."""
    ma = _metrics(a)
    mb = _metrics(b)
    deltas: dict[str, float | None] = {}
    for key in _KEYS:
        va, vb = ma.get(key), mb.get(key)
        if va is None or vb is None:
            deltas[key] = None
        else:
            deltas[key] = float(vb) - float(va)
    return {
        "a": {
            "id": a.get("id"),
            "provider": a.get("provider"),
            "prompt_version": a.get("prompt_version"),
            "metrics": ma,
        },
        "b": {
            "id": b.get("id"),
            "provider": b.get("provider"),
            "prompt_version": b.get("prompt_version"),
            "metrics": mb,
        },
        "delta_b_minus_a": deltas,
    }


def _metrics(row: dict[str, Any]) -> dict[str, Any]:
    nested = row.get("metrics") if isinstance(row.get("metrics"), dict) else None
    src = nested or row
    out: dict[str, Any] = {}
    for key in _KEYS:
        val = src.get(key)
        out[key] = None if val is None else float(val)
    if src.get("case_count") is not None:
        out["case_count"] = src.get("case_count")
    else:
        out["case_count"] = row.get("case_count")
    return out
