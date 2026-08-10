"""HUD query helpers over RunStore (aggregations + allow-listed DTOs)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from questline.core.errors import Verdict
from questline.core.store import RunStore
from questline.reporters.summary import build_run_summary

# Fields safe to expose over the local HUD API (viewer only; still allow-listed).
_ARTIFACT_KEYS = ("run_id", "test_id", "path", "kind", "size_bytes", "timestamp", "type")


def parse_meta(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def duration_seconds(started_at: Any, finished_at: Any) -> float | None:
    start = _parse_dt(started_at)
    end = _parse_dt(finished_at)
    if start is None or end is None:
        return None
    return max(0.0, (end - start).total_seconds())


def enrich_run(store: RunStore, run: dict[str, Any]) -> dict[str, Any]:
    """Run row + totals / verdict split / meta driver-device."""
    run_id = str(run.get("id") or "")
    summary = build_run_summary(store, run_id)
    meta = parse_meta(run.get("meta"))
    duration = duration_seconds(run.get("started_at"), run.get("finished_at"))
    if duration is None:
        duration = summary.duration_s
    return {
        "id": run_id,
        "profile": run.get("profile") or summary.profile,
        "status": run.get("status") or summary.status,
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "duration_s": duration,
        "driver": meta.get("driver") or summary.driver,
        "device": meta.get("device") or summary.device,
        "passed": summary.passed,
        "failed": summary.failed,
        "skipped": summary.skipped,
        "error": summary.error,
        "total": summary.total,
        "infra_failures": summary.infra_failures,
        "test_failures": summary.test_failures,
        "authoring_failures": summary.authoring_failures,
        "unknown_failures": summary.unknown_failures,
    }


def enrich_test(store: RunStore, row: dict[str, Any]) -> dict[str, Any]:
    test_id = str(row.get("id") or "")
    duration = duration_seconds(row.get("started_at"), row.get("finished_at"))
    death = store.death_point(test_id) if test_id else {}
    last_started = death.get("last_started_step") if isinstance(death, dict) else None
    death_name = None
    if isinstance(last_started, dict):
        death_name = last_started.get("name")
    elif isinstance(death, dict):
        last_finished = death.get("last_finished_step")
        if isinstance(last_finished, dict):
            death_name = last_finished.get("name")
    return {
        "id": test_id,
        "run_id": row.get("run_id"),
        "nodeid": row.get("nodeid"),
        "status": row.get("status"),
        "verdict": row.get("verdict"),
        "error_type": row.get("error_type"),
        "error_message": row.get("error_message"),
        "feature_id": row.get("feature_id"),
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "duration_s": duration,
        "death_step_name": death_name,
    }


def allowlisted_artifact(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in _ARTIFACT_KEYS:
        if key in payload and payload[key] is not None:
            out[key] = payload[key]
    # Expose basename only for UI labels; full path used server-side for serving.
    path = payload.get("path")
    if isinstance(path, str) and path:
        # Normalize Windows separators so basename works on Linux CI too.
        out["name"] = Path(path.replace("\\", "/")).name
    return out


def trends(store: RunStore, *, limit_runs: int = 50) -> dict[str, Any]:
    """Pass-rate / duration over recent runs + flakiness board by nodeid."""
    runs = store.list_runs(limit=limit_runs, offset=0)
    series: list[dict[str, Any]] = []
    by_node: dict[str, list[str]] = {}

    for run in reversed(runs):  # chronological for charts
        enriched = enrich_run(store, run)
        total = int(enriched["total"] or 0)
        passed = int(enriched["passed"] or 0)
        pass_rate = (passed / total) if total else None
        series.append(
            {
                "run_id": enriched["id"],
                "started_at": enriched["started_at"],
                "profile": enriched["profile"],
                "status": enriched["status"],
                "pass_rate": pass_rate,
                "duration_s": enriched["duration_s"],
                "passed": passed,
                "failed": enriched["failed"],
                "total": total,
                "infra_failures": enriched["infra_failures"],
                "test_failures": enriched["test_failures"],
            }
        )
        for test in store.list_tests(str(run.get("id") or "")):
            nodeid = str(test.get("nodeid") or "")
            status = str(test.get("status") or "").lower()
            if not nodeid:
                continue
            by_node.setdefault(nodeid, []).append(status)

    flaky: list[dict[str, Any]] = []
    for nodeid, statuses in by_node.items():
        if len(statuses) < 2:
            continue
        passes = sum(1 for s in statuses if s == "passed")
        fails = sum(1 for s in statuses if s in {"failed", "error"})
        if passes == 0 or fails == 0:
            continue
        flaky.append(
            {
                "nodeid": nodeid,
                "runs": len(statuses),
                "passed": passes,
                "failed": fails,
                "pass_rate": passes / len(statuses),
                "flake_score": min(passes, fails) / len(statuses),
            }
        )
    flaky.sort(key=lambda r: (-float(r["flake_score"]), -int(r["runs"])))

    return {
        "series": series,
        "flaky_tests": flaky[:30],
        "verdicts": {
            "infra": Verdict.INFRA.value,
            "test": Verdict.TEST.value,
            "authoring": Verdict.AUTHORING.value,
            "unknown": Verdict.UNKNOWN.value,
        },
    }


def test_history_sparkline(
    store: RunStore, nodeid: str, *, limit: int = 20
) -> list[dict[str, Any]]:
    rows = store.list_tests_by_nodeid(nodeid, limit=limit)
    # Oldest → newest for sparkline left-to-right
    out: list[dict[str, Any]] = []
    for row in reversed(rows):
        out.append(
            {
                "run_id": row.get("run_id"),
                "test_id": row.get("id"),
                "status": row.get("status"),
                "verdict": row.get("verdict"),
                "started_at": row.get("started_at"),
                "duration_s": duration_seconds(row.get("started_at"), row.get("finished_at")),
            }
        )
    return out


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
