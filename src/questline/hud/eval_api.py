"""HUD REST for phase-13 eval harness (history, compare, run)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from questline.core.store import RunStore
from questline.evalharness.compare import compare_eval_runs
from questline.evalharness.persist import load_eval_artifact
from questline.evalharness.runner import run_eval
from questline.lens.browse import public_path

router = APIRouter(prefix="/api")


class EvalRunBody(BaseModel):
    agent: str = "maintainer"
    provider: str = "fake"
    prompt_version: str = Field(default="v1")


def _store(request: Request) -> RunStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="run store not configured")
    return store  # type: ignore[no-any-return]


def _row_public(
    store: RunStore, row: dict[str, Any], *, include_body: bool = False
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.get("id"),
        "agent": row.get("agent"),
        "provider": row.get("provider"),
        "prompt_version": row.get("prompt_version"),
        "status": row.get("status"),
        "diagnosis_accuracy": row.get("diagnosis_accuracy"),
        "fix_correctness": row.get("fix_correctness"),
        "false_green_rate": row.get("false_green_rate"),
        "iterations_avg": row.get("iterations_avg"),
        "cost_usd": row.get("cost_usd"),
        "case_count": row.get("case_count"),
        "created_at": row.get("created_at"),
        "artifact": public_path(store, row.get("artifact_path")),
    }
    if include_body:
        body = load_eval_artifact(row.get("artifact_path"))
        if body:
            out["cases"] = body.get("cases") or []
            out["metrics"] = body.get("metrics") or {}
            out["meta"] = body.get("meta") or {}
    return out


@router.get("/eval/runs")
def list_eval_runs(request: Request) -> dict[str, Any]:
    store = _store(request)
    rows = store.list_eval_results()
    return {"runs": [_row_public(store, r) for r in rows], "empty": len(rows) == 0}


@router.get("/eval/runs/{eval_id}")
def get_eval_run(eval_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    row = store.get_eval_result(eval_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"eval run not found: {eval_id}")
    return {"run": _row_public(store, row, include_body=True)}


@router.get("/eval/compare")
def compare_evals(
    request: Request,
    a: str = Query(..., min_length=1),
    b: str = Query(..., min_length=1),
) -> dict[str, Any]:
    store = _store(request)
    ra = store.get_eval_result(a)
    rb = store.get_eval_result(b)
    if ra is None:
        raise HTTPException(status_code=404, detail=f"eval run not found: {a}")
    if rb is None:
        raise HTTPException(status_code=404, detail=f"eval run not found: {b}")
    left = _row_public(store, ra, include_body=True)
    right = _row_public(store, rb, include_body=True)
    return {"compare": compare_eval_runs(left, right)}


@router.post("/eval/run")
def post_eval_run(body: EvalRunBody, request: Request) -> dict[str, Any]:
    """Offline golden eval (FakeProvider + injected gate). Live providers stay CLI."""
    store = _store(request)
    run = run_eval(
        store,
        agent=body.agent,
        provider=body.provider or "fake",
        prompt_version=body.prompt_version or "v1",
    )
    row = store.get_eval_result(run.id)
    if row is None:
        raise HTTPException(status_code=500, detail="eval run did not persist")
    return {"run": _row_public(store, row, include_body=True)}
