"""HUD REST API over RunStore."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from questline.core.store import RunStore
from questline.hud.queries import (
    allowlisted_artifact,
    enrich_run,
    enrich_test,
    test_history_sparkline,
    trends,
)

router = APIRouter(prefix="/api")


def _store(request: Request) -> RunStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="run store not configured")
    return store  # type: ignore[no-any-return]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/runs")
def list_runs(
    request: Request,
    profile: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    store = _store(request)
    rows = store.list_runs(profile=profile, status=status, limit=limit, offset=offset)
    return {"runs": [enrich_run(store, r) for r in rows], "empty": len(rows) == 0}


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    tests = [enrich_test(store, t) for t in store.list_tests(run_id)]
    enriched = enrich_run(store, run)
    return {
        "run": enriched,
        "tests": tests,
        "banner": {
            "infra_failures": enriched["infra_failures"],
            "test_failures": enriched["test_failures"],
            "authoring_failures": enriched["authoring_failures"],
            "unknown_failures": enriched["unknown_failures"],
        },
    }


@router.get("/runs/{run_id}/tests/{test_id}")
def get_test(run_id: str, test_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    test = store.get_test(test_id)
    if test is None or str(test.get("run_id")) != run_id:
        raise HTTPException(status_code=404, detail=f"test not found: {test_id}")
    steps = store.list_steps(test_id)
    death = store.death_point(test_id)
    artifacts = [
        allowlisted_artifact(a)
        for a in store.list_artifacts(run_id=run_id, test_id=test_id)
    ]
    enriched = enrich_test(store, test)
    history = test_history_sparkline(store, str(test.get("nodeid") or ""))
    return {
        "test": enriched,
        "steps": steps,
        "death_point": death,
        "artifacts": artifacts,
        "history": history,
    }


@router.get("/runs/{run_id}/artifacts")
def list_run_artifacts(run_id: str, request: Request) -> dict[str, Any]:
    store = _store(request)
    if store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    artifacts = [allowlisted_artifact(a) for a in store.list_artifacts(run_id=run_id)]
    return {"artifacts": artifacts}


@router.get("/artifacts/file")
def get_artifact_file(
    request: Request,
    path: str = Query(..., description="Absolute artifact path from store"),
) -> FileResponse:
    """Serve an artifact file only if it lives under the store artifacts_dir."""
    store = _store(request)
    root = store.artifacts_dir.resolve()
    try:
        target = Path(path).resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail="invalid path") from exc
    if root not in target.parents and target != root:
        raise HTTPException(status_code=403, detail="path outside artifacts dir")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    media, _ = mimetypes.guess_type(str(target))
    return FileResponse(target, media_type=media or "application/octet-stream")


@router.get("/trends")
def get_trends(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    store = _store(request)
    return trends(store, limit_runs=limit)
