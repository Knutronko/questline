"""HUD GameLens + telemetry + balance-agent REST (FP-G4)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from questline.core.errors import AuthoringError
from questline.core.store import RunStore
from questline.lens.agent import load_turn_artifact, run_balance_agent
from questline.lens.browse import (
    SnapshotNotFoundError,
    diff_from_store,
    implications_for_pair,
    implications_payload,
    implications_row_public,
    list_sessions_public,
    list_snapshots_public,
    public_path,
    resolve_snapshot_row,
    session_public,
    snapshot_row_public,
)

router = APIRouter(prefix="/api")


class AgentRunBody(BaseModel):
    snapshot_a: str
    snapshot_b: str
    question: str | None = None
    profile: str | None = Field(
        default=None, description="questline.toml profile (ai_groq / ai_ollama)"
    )


def _store(request: Request) -> RunStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="run store not configured")
    return store  # type: ignore[no-any-return]


def _ai_calls_payload(store: RunStore, run_id: str) -> dict[str, Any]:
    rows = store.list_ai_calls(run_id=run_id)
    calls = []
    total = 0.0
    for row in rows:
        cost = float(row.get("cost") or 0.0)
        total += cost
        calls.append(
            {
                "provider": row.get("provider"),
                "model": row.get("model"),
                "tokens_in": row.get("tokens_in"),
                "tokens_out": row.get("tokens_out"),
                "cost": cost,
                "purpose": row.get("purpose"),
                "duration_ms": row.get("duration_ms"),
                "outcome": row.get("outcome"),
                "cached": bool(row.get("cached")),
                "timestamp": row.get("timestamp"),
            }
        )
    return {"run_id": run_id, "calls": calls, "total_usd": total}


def _turn_public(
    store: RunStore, row: dict[str, Any], *, include_body: bool = False
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.get("id"),
        "snapshot_id_a": row.get("snapshot_id_a"),
        "snapshot_id_b": row.get("snapshot_id_b"),
        "question": row.get("question"),
        "status": row.get("status"),
        "framing": row.get("framing"),
        "prompt_version": row.get("prompt_version"),
        "created_at": row.get("created_at"),
        "artifact": public_path(store, row.get("artifact_path")),
    }
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    out["pending"] = meta.get("pending")
    out["gap_count"] = meta.get("gap_count")
    out["tool_count"] = meta.get("tool_count")
    if include_body:
        body = load_turn_artifact(row.get("artifact_path"))
        if body:
            out["summary"] = body.get("summary")
            out["priorities"] = body.get("priorities") or []
            out["gaps"] = body.get("gaps") or []
            out["citations"] = body.get("citations") or {}
            out["tool_log"] = body.get("tool_log") or []
            out["pending"] = body.get("pending", out.get("pending"))
            out["purpose_tag"] = body.get("purpose_tag")
        costs = _ai_calls_payload(store, str(row.get("id") or ""))
        out["ai_calls"] = costs["calls"]
        out["ai_cost_total"] = costs["total_usd"]
    return out


@router.get("/lens/snapshots")
def list_snapshots(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    store = _store(request)
    rows = list_snapshots_public(store, limit=limit)
    return {"snapshots": rows, "empty": len(rows) == 0}


@router.get("/lens/snapshots/{key}")
def get_snapshot(key: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    try:
        row = resolve_snapshot_row(store, key)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"snapshot not found: {exc}") from exc
    return {"snapshot": snapshot_row_public(store, row)}


@router.get("/lens/diff")
def get_diff(
    request: Request,
    a: str = Query(..., min_length=1),
    b: str = Query(..., min_length=1),
) -> dict[str, Any]:
    store = _store(request)
    try:
        report = diff_from_store(store, a, b)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"snapshot not found: {exc}") from exc
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    implications = implications_for_pair(store, a, b)
    return {"diff": report.to_dict(), "implications": implications}


@router.get("/lens/implications")
def list_implications(
    request: Request,
    snapshot_id_a: str | None = None,
    snapshot_id_b: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    store = _store(request)
    rows = store.list_lens_implications(
        snapshot_id_a=snapshot_id_a,
        snapshot_id_b=snapshot_id_b,
        limit=limit,
    )
    return {
        "implications": [implications_row_public(store, row) for row in rows],
        "empty": len(rows) == 0,
    }


@router.get("/lens/implications/{pair_id}")
def get_implications(pair_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    payload = implications_payload(store, pair_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"implications not found: {pair_id}")
    return {"implications": payload}


@router.get("/telemetry/sessions")
def list_sessions(
    request: Request,
    config_snapshot_id: str | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    store = _store(request)
    rows = list_sessions_public(
        store, config_snapshot_id=config_snapshot_id, limit=limit
    )
    return {"sessions": rows, "empty": len(rows) == 0}


@router.get("/telemetry/sessions/{session_id}")
def get_session(session_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    row = store.get_telemetry_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    payload = session_public(row, include_summary=True)
    payload["event_count"] = store.count_telemetry_events(str(row["id"]))
    return {"session": payload}


@router.get("/lens/agent/turns")
def list_agent_turns(
    request: Request,
    snapshot_id_a: str | None = None,
    snapshot_id_b: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    store = _store(request)
    rows = store.list_lens_agent_turns(
        snapshot_id_a=snapshot_id_a,
        snapshot_id_b=snapshot_id_b,
        limit=limit,
    )
    return {
        "turns": [_turn_public(store, row) for row in rows],
        "empty": len(rows) == 0,
    }


@router.get("/lens/agent/turns/{turn_id}")
def get_agent_turn(turn_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    row = store.get_lens_agent_turn(turn_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"agent turn not found: {turn_id}")
    return {"turn": _turn_public(store, row, include_body=True)}


@router.post("/lens/agent/run")
def run_agent(body: AgentRunBody, request: Request) -> dict[str, Any]:
    store = _store(request)
    try:
        diff_from_store(store, body.snapshot_a, body.snapshot_b)
    except SnapshotNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"snapshot not found: {exc}") from exc
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    turn_id = f"ba-{uuid.uuid4().hex[:16]}"
    router_impl = _agent_router(request, store, body.profile, run_id=turn_id)
    turn = run_balance_agent(
        store,
        snapshot_a=body.snapshot_a,
        snapshot_b=body.snapshot_b,
        question=body.question,
        router=router_impl,
        turn_id=turn_id,
    )
    row = store.get_lens_agent_turn(turn.id)
    if row is None:
        raise HTTPException(status_code=500, detail="agent turn did not persist")
    return {"turn": _turn_public(store, row, include_body=True)}


def _agent_router(
    request: Request, store: RunStore, profile: str | None, *, run_id: str
) -> Any:
    """Build a router without importing ``questline.ai.factory`` (cursor_cli isolated)."""
    injected = getattr(request.app.state, "llm_provider", None)
    if injected is not None:
        from questline.ai.router import ProviderRouter

        return ProviderRouter(
            [injected],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id=run_id,
        )
    import os

    from questline.ai.pricing import load_pricing
    from questline.ai.providers.fake import FakeProvider
    from questline.ai.providers.ollama import OllamaProvider
    from questline.ai.providers.openai_compat import OpenAICompatProvider
    from questline.ai.router import ProviderRouter
    from questline.core.config import load_settings

    cfg = getattr(request.app.state, "config_path", None)
    root = getattr(request.app.state, "project_root", None)
    name = (profile or "").strip() or "ai_groq"
    try:
        settings = load_settings(
            config_path=cfg,
            profile=name,
            project_root=root,
        )
    except AuthoringError:
        return None
    env = dict(os.environ)
    providers: list[Any] = []
    names = list(settings.ai.candidates) or list(settings.ai.providers)
    for item in names:
        spec = settings.ai.providers.get(item)
        if spec is None:
            continue
        kind = spec.kind.strip().lower()
        if kind == "cursor_cli":
            continue
        if kind == "ollama":
            providers.append(
                OllamaProvider(
                    name=item,
                    base_url=spec.base_url or "http://127.0.0.1:11434",
                    model=spec.model or "llama3.2",
                    timeout_s=spec.timeout_s,
                )
            )
            continue
        if kind == "fake":
            providers.append(FakeProvider(name=item, model=spec.model or "fake-test"))
            continue
        if kind == "openai_compat":
            key_name = spec.api_key_env or ""
            if not key_name or not (env.get(key_name) or "").strip():
                continue
            if not spec.base_url or not spec.model:
                continue
            providers.append(
                OpenAICompatProvider(
                    name=item,
                    base_url=spec.base_url,
                    model=spec.model,
                    api_key_env=key_name,
                    environ=env,
                    timeout_s=spec.timeout_s,
                )
            )
    if not providers:
        return None
    return ProviderRouter(
        providers,
        budget_per_call_usd=settings.ai.budget_per_call_usd,
        budget_per_run_usd=settings.ai.budget_per_run_usd,
        store=store,
        run_id=run_id,
        pricing=load_pricing(),
        models=dict(settings.ai.models),
    )
