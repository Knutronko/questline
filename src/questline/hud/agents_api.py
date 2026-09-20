"""HUD REST for phase-12 test agents (triage / diagnose / heal)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from questline.ai.agents.healer import run_healer
from questline.ai.agents.maintainer import run_maintainer
from questline.ai.agents.persist import load_task_artifact
from questline.ai.agents.triage import run_triage
from questline.core.store import RunStore
from questline.hud.ai_router import build_hud_router
from questline.lens.browse import public_path

router = APIRouter(prefix="/api")


class TriageBody(BaseModel):
    run_id: str
    profile: str | None = Field(default=None)


class DiagnoseBody(BaseModel):
    run_id: str
    test_id: str
    profile: str | None = None
    fix: bool = False
    flaky_guard: bool = False


class HealBody(BaseModel):
    run_id: str
    test_id: str | None = None
    profile: str | None = None


def _store(request: Request) -> RunStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="run store not configured")
    return store  # type: ignore[no-any-return]


def _root(request: Request) -> Path:
    root = getattr(request.app.state, "project_root", None)
    return Path(root).resolve() if root else Path.cwd().resolve()


def _task_public(
    store: RunStore, row: dict[str, Any], *, include_body: bool = False
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.get("id"),
        "kind": row.get("kind"),
        "run_id": row.get("run_id"),
        "test_id": row.get("test_id"),
        "status": row.get("status"),
        "verdict": row.get("verdict"),
        "cause": row.get("cause"),
        "prompt_version": row.get("prompt_version"),
        "created_at": row.get("created_at"),
        "artifact": public_path(store, row.get("artifact_path")),
    }
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    out["pending"] = meta.get("pending")
    out["tool_count"] = meta.get("tool_count")
    if include_body:
        body = load_task_artifact(row.get("artifact_path"))
        if body:
            out["summary"] = body.get("summary")
            out["clusters"] = body.get("clusters") or []
            out["evidence"] = body.get("evidence") or []
            out["suggestion"] = body.get("suggestion")
            out["gate"] = body.get("gate")
            out["tool_log"] = body.get("tool_log") or []
            out["agent_claim"] = body.get("agent_claim")
        costs = store.list_ai_calls(run_id=str(row.get("run_id") or ""))
        tagged = [c for c in costs if str(c.get("purpose") or "").startswith("agent.")]
        out["ai_calls"] = [
            {
                "provider": c.get("provider"),
                "model": c.get("model"),
                "cost": c.get("cost"),
                "purpose": c.get("purpose"),
                "outcome": c.get("outcome"),
            }
            for c in tagged
        ]
        out["ai_cost_total"] = sum(float(c.get("cost") or 0.0) for c in tagged)
    return out


@router.get("/runs/{run_id}/agent-tasks")
def list_run_agent_tasks(run_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    if store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    rows = store.list_agent_tasks(run_id=run_id)
    return {
        "run_id": run_id,
        "tasks": [_task_public(store, r) for r in rows],
        "empty": len(rows) == 0,
    }


@router.get("/agent-tasks/{task_id}")
def get_agent_task(task_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    row = store.get_agent_task(task_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"agent task not found: {task_id}")
    return {"task": _task_public(store, row, include_body=True)}


@router.post("/agents/triage")
def post_triage(body: TriageBody, request: Request) -> dict[str, Any]:
    store = _store(request)
    if store.get_run(body.run_id) is None:
        raise HTTPException(status_code=404, detail=f"run not found: {body.run_id}")
    router_impl = build_hud_router(request, store, body.profile, run_id=body.run_id)
    task = run_triage(
        store,
        run_id=body.run_id,
        router=router_impl,
        project_root=_root(request),
    )
    row = store.get_agent_task(task.id)
    if row is None:
        raise HTTPException(status_code=500, detail="agent task did not persist")
    return {"task": _task_public(store, row, include_body=True)}


@router.post("/agents/diagnose")
def post_diagnose(body: DiagnoseBody, request: Request) -> dict[str, Any]:
    store = _store(request)
    test_id = unquote(body.test_id)
    if store.get_test(test_id) is None:
        raise HTTPException(status_code=404, detail=f"test not found: {test_id}")
    router_impl = build_hud_router(request, store, body.profile, run_id=body.run_id)
    qpath = getattr(request.app.state, "quarantine_path", None)
    task = run_maintainer(
        store,
        run_id=body.run_id,
        test_id=test_id,
        router=router_impl,
        project_root=_root(request),
        quarantine_path=Path(qpath) if qpath else None,
        fix=body.fix,
        flaky_guard=body.flaky_guard,
    )
    row = store.get_agent_task(task.id)
    if row is None:
        raise HTTPException(status_code=500, detail="agent task did not persist")
    return {"task": _task_public(store, row, include_body=True)}


@router.post("/agents/heal")
def post_heal(body: HealBody, request: Request) -> dict[str, Any]:
    store = _store(request)
    if store.get_run(body.run_id) is None:
        raise HTTPException(status_code=404, detail=f"run not found: {body.run_id}")
    test_id = unquote(body.test_id) if body.test_id else None
    router_impl = build_hud_router(request, store, body.profile, run_id=body.run_id)
    root = _root(request)
    try:
        task = run_healer(
            store,
            run_id=body.run_id,
            test_id=test_id,
            router=router_impl,
            project_root=root,
            locators_path=root / "locators.yaml",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    row = store.get_agent_task(task.id)
    if row is None:
        raise HTTPException(status_code=500, detail="agent task did not persist")
    return {"task": _task_public(store, row, include_body=True)}
