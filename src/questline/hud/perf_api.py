"""Perf series + build-over-build compare for HUD graphs."""

from __future__ import annotations

from typing import Any

from questline.core.store import RunStore
from questline.perf.report import summarize_perf_samples


def perf_series_for_run(
    store: RunStore,
    run_id: str,
    *,
    test_id: str | None = None,
    metric: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    if store.get_run(run_id) is None:
        return {"run_id": run_id, "found": False, "samples": [], "summary": {}, "series": {}}
    samples = store.list_perf_samples(
        run_id=run_id, test_id=test_id, metric=metric, limit=limit
    )
    summary = summarize_perf_samples(samples)
    by_metric: dict[str, list[dict[str, Any]]] = {}
    for row in samples:
        m = str(row.get("metric") or "")
        if not m:
            continue
        by_metric.setdefault(m, []).append(
            {
                "t": row.get("timestamp"),
                "v": row.get("value"),
                "test_id": row.get("test_id"),
            }
        )
    return {
        "run_id": run_id,
        "found": True,
        "samples": samples,
        "summary": summary,
        "series": by_metric,
    }


def compare_perf_runs(
    store: RunStore,
    run_a: str,
    run_b: str,
) -> dict[str, Any]:
    a = perf_series_for_run(store, run_a)
    b = perf_series_for_run(store, run_b)
    metrics = sorted(set(a["summary"]) | set(b["summary"]))
    deltas: list[dict[str, Any]] = []
    for metric in metrics:
        sa = a["summary"].get(metric) or {}
        sb = b["summary"].get(metric) or {}
        avg_a = float(sa["avg"]) if "avg" in sa else None
        avg_b = float(sb["avg"]) if "avg" in sb else None
        delta_avg = None
        if avg_a is not None and avg_b is not None:
            delta_avg = avg_b - avg_a
        deltas.append(
            {
                "metric": metric,
                "a": sa,
                "b": sb,
                "delta_avg": delta_avg,
            }
        )
    return {
        "run_a": run_a,
        "run_b": run_b,
        "found_a": a["found"],
        "found_b": b["found"],
        "deltas": deltas,
        "series_a": a["series"],
        "series_b": b["series"],
        "summary_a": a["summary"],
        "summary_b": b["summary"],
    }


def duration_pass_correlation(store: RunStore, *, limit: int = 50) -> list[dict[str, Any]]:
    """Per-nodeid points for flakiness board: duration vs pass (phase-10)."""
    runs = store.list_runs(limit=limit)
    # nodeid → list of {duration_s, passed}
    buckets: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        rid = str(run["id"])
        for test in store.list_tests(rid):
            nodeid = str(test.get("nodeid") or "")
            if not nodeid:
                continue
            status = str(test.get("status") or "")
            dur = test.get("duration_s")
            try:
                duration_s = float(dur) if dur is not None else None
            except (TypeError, ValueError):
                duration_s = None
            buckets.setdefault(nodeid, []).append(
                {
                    "run_id": rid,
                    "duration_s": duration_s,
                    "passed": status == "passed",
                    "status": status,
                }
            )
    out: list[dict[str, Any]] = []
    for nodeid, points in sorted(buckets.items()):
        if len(points) < 2:
            continue
        passed = sum(1 for p in points if p["passed"])
        failed = len(points) - passed
        if passed == 0 or failed == 0:
            continue
        out.append(
            {
                "nodeid": nodeid,
                "points": points,
                "runs": len(points),
                "passed": passed,
                "failed": failed,
            }
        )
    return out
