"""Aggregate eval metrics. Numbers come from gates, not model claims."""

from __future__ import annotations

from typing import Any


def score_case(
    *,
    cause_expected: str,
    cause_actual: str | None,
    expected_fix_class: str,
    actual_fix_class: str | None,
    score_fix: bool,
    gate_accepted: bool,
    actually_green: bool,
    sabotage: bool,
    iterations: int,
    cost_usd: float,
) -> dict[str, Any]:
    diagnosis_ok = (cause_actual or "unknown") == cause_expected
    false_green = bool(gate_accepted) and not actually_green
    if sabotage:
        # A sabotaged gate that reports green while the test is still red
        # must always count as a false-green, even if the agent was honest.
        false_green = bool(gate_accepted) and not actually_green
    if score_fix:
        class_ok = (actual_fix_class or "") == expected_fix_class
        fix_ok = bool(gate_accepted) and actually_green and class_ok and not false_green
    else:
        fix_ok = None
    return {
        "diagnosis_ok": diagnosis_ok,
        "fix_ok": fix_ok,
        "false_green": false_green,
        "iterations": iterations,
        "cost_usd": cost_usd,
        "gate_accepted": gate_accepted,
        "actually_green": actually_green,
        "sabotage": sabotage,
        "expected_fix_class": expected_fix_class,
        "actual_fix_class": actual_fix_class,
    }


def aggregate(case_rows: list[dict[str, Any]]) -> dict[str, float]:
    n = len(case_rows) or 1
    diag = [r for r in case_rows if r.get("cause_expected")]
    diag_ok = sum(1 for r in diag if r.get("diagnosis_ok"))
    fix_rows = [r for r in case_rows if r.get("score_fix")]
    fix_ok = sum(1 for r in fix_rows if r.get("fix_ok"))
    gated = [r for r in case_rows if r.get("mode") == "fix" or r.get("sabotage")]
    if not gated:
        gated = case_rows
    false_g = sum(1 for r in gated if r.get("false_green"))
    iters = [float(r.get("iterations") or 0) for r in case_rows]
    cost = sum(float(r.get("cost_usd") or 0.0) for r in case_rows)
    return {
        "diagnosis_accuracy": (diag_ok / len(diag)) if diag else 0.0,
        "fix_correctness": (fix_ok / len(fix_rows)) if fix_rows else 0.0,
        "false_green_rate": (false_g / len(gated)) if gated else 0.0,
        "iterations_avg": (sum(iters) / n),
        "cost_usd": cost,
    }
