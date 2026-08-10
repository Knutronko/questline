"""Build RunSummary from the sealed RunStore (verdicts from store, not claims)."""

from __future__ import annotations

from typing import Any

from questline.core.errors import Verdict
from questline.core.store import RunStore
from questline.reporters.port import RunSummary, TestResultSummary


def build_run_summary(
    store: RunStore,
    run_id: str,
    *,
    profile: str | None = None,
    driver: str | None = None,
    device: str | None = None,
    html_path: str | None = None,
) -> RunSummary:
    """Assemble an allow-list-friendly summary from persisted store rows."""
    run = store.get_run(run_id) or {}
    tests_raw = store.list_tests(run_id)

    passed = failed = skipped = error = 0
    infra = test_v = authoring = unknown = 0
    tests: list[TestResultSummary] = []

    for row in tests_raw:
        status = (row.get("status") or "unknown").lower()
        if status == "passed":
            passed += 1
        elif status == "skipped":
            skipped += 1
        elif status == "error":
            error += 1
        else:
            failed += 1

        verdict = row.get("verdict")
        if status in {"failed", "error"} and verdict:
            if verdict == Verdict.INFRA.value:
                infra += 1
            elif verdict == Verdict.TEST.value:
                test_v += 1
            elif verdict == Verdict.AUTHORING.value:
                authoring += 1
            else:
                unknown += 1
        elif status in {"failed", "error"}:
            unknown += 1

        death_step = _death_step_name(store, row.get("id") or "")
        tests.append(
            TestResultSummary(
                test_id=str(row.get("id") or ""),
                nodeid=str(row.get("nodeid") or ""),
                status=status,
                verdict=verdict,
                error_type=row.get("error_type"),
                error_message=row.get("error_message"),
                duration_s=_as_float(row.get("duration_s")),
                death_step_name=death_step,
                feature_id=row.get("feature_id"),
            )
        )

    return RunSummary(
        run_id=run_id,
        profile=profile or str(run.get("profile") or ""),
        status=str(run.get("status") or "unknown"),
        duration_s=_as_float(run.get("duration_s")),
        driver=driver,
        device=device,
        passed=passed,
        failed=failed,
        skipped=skipped,
        error=error,
        infra_failures=infra,
        test_failures=test_v,
        authoring_failures=authoring,
        unknown_failures=unknown,
        tests=tuple(tests),
        html_path=html_path,
    )


def _death_step_name(store: RunStore, test_id: str) -> str | None:
    if not test_id:
        return None
    dp = store.death_point(test_id)
    step = dp.get("last_started_step") or dp.get("last_finished_step")
    if not isinstance(step, dict):
        return None
    name = step.get("name")
    return str(name) if name else None


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
