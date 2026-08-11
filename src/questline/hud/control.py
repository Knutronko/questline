"""HUD control-center REST (launcher, quarantine, config, devices, perf)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from questline.core.errors import AuthoringError, DeviceError
from questline.hud.config_edit import (
    get_profile_public,
    list_profile_names,
    preview_and_save_profile,
    validate_profile_patch,
)
from questline.hud.launcher import LaunchRequest, RunLauncher
from questline.hud.perf_api import compare_perf_runs, duration_pass_correlation, perf_series_for_run
from questline.hud.security import CSRF_COOKIE, new_csrf_token
from questline.reporters.registry import KNOWN_REPORTERS

router = APIRouter(prefix="/api")


class LaunchBody(BaseModel):
    profile: str = "default"
    tests: list[str] = Field(default_factory=list)
    markers: str | None = None
    device_serial: str | None = None
    reporters: list[str] | None = None
    include_quarantined: bool = False


class ProfileBody(BaseModel):
    fields: dict[str, Any]
    apply: bool = False


class QuarantineAddBody(BaseModel):
    test_id: str
    reason: str
    owner: str
    exit_criteria: str
    issue: str | None = None
    feature: str | None = None


class QuarantineAuditBody(BaseModel):
    tests: list[str] | None = None
    rootdir: str | None = None


def _state(request: Request) -> Any:
    return request.app.state


def _launcher(request: Request) -> RunLauncher:
    launcher = getattr(_state(request), "launcher", None)
    if launcher is None:
        raise HTTPException(status_code=503, detail="run launcher not configured")
    return launcher  # type: ignore[no-any-return]


def _config_path(request: Request) -> Path:
    path = getattr(_state(request), "config_path", None)
    if path is None:
        raise HTTPException(status_code=503, detail="config path not configured")
    return Path(path)


def _project_root(request: Request) -> Path:
    root = getattr(_state(request), "project_root", None)
    return Path(root) if root is not None else _config_path(request).parent


def _quarantine_path(request: Request) -> Path:
    path = getattr(_state(request), "quarantine_path", None)
    if path is not None:
        return Path(path)
    return _project_root(request) / "quarantine.yaml"


def _read_only(request: Request) -> bool:
    return bool(getattr(_state(request), "read_only", False))


@router.get("/meta")
def meta(request: Request) -> dict[str, Any]:
    cfg = getattr(_state(request), "config_path", None)
    return {
        "read_only": _read_only(request),
        "control_center": not _read_only(request),
        "config_path": str(_config_path(request)) if cfg else None,
        "project_root": str(_project_root(request)),
        "quarantine_path": str(_quarantine_path(request)),
        "reporters": sorted(KNOWN_REPORTERS),
    }


@router.get("/csrf")
def csrf_token(request: Request, response: Response) -> dict[str, str]:
    token = new_csrf_token()
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=False,
        samesite="strict",
        path="/",
    )
    launcher = getattr(_state(request), "launcher", None)
    if launcher is not None and hasattr(launcher, "csrf_token"):
        launcher.csrf_token = token
    return {"csrf_token": token, "header": "X-CSRF-Token", "cookie": CSRF_COOKIE}


@router.post("/live/ingest")
def live_ingest(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, str]:
    """Accept forwarded EventBus payloads from a HUD-launched pytest subprocess."""
    bridge = getattr(_state(request), "live", None)
    if bridge is None:
        raise HTTPException(status_code=503, detail="live bridge not configured")
    if not isinstance(payload, dict) or "type" not in payload:
        raise HTTPException(status_code=400, detail="payload must be an event dict with type")
    bridge.broadcast_payload(payload)
    return {"status": "ok"}


@router.get("/devices")
def list_devices(request: Request) -> dict[str, Any]:
    """Live device list via LocalAdbProvider (best-effort; empty if adb missing)."""
    try:
        from questline.devices.adb.provider import LocalAdbProvider

        provider = LocalAdbProvider()
        devices = provider.list_devices()
        return {
            "devices": [
                {
                    "id": d.id,
                    "platform": d.platform,
                    "api_level": d.api_level,
                    "caps": dict(d.caps),
                }
                for d in devices
            ]
        }
    except Exception as exc:
        return {"devices": [], "error": str(exc)}


@router.get("/reporters")
def list_reporters() -> dict[str, Any]:
    return {"reporters": sorted(KNOWN_REPORTERS)}


@router.get("/tests/collect")
def collect_tests(
    request: Request,
    path: str = Query(".", description="Pytest path to collect"),
    limit: int = Query(500, ge=1, le=5000),
) -> dict[str, Any]:
    """Collect nodeids via pytest --collect-only (same public surface as CLI)."""
    import subprocess
    import sys

    root = _project_root(request)
    argv = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        path,
    ]
    try:
        proc = subprocess.run(
            argv,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="pytest collect timed out") from exc
    nodeids: list[str] = []
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if "::" in line and not line.startswith("="):
            nodeids.append(line)
    return {
        "nodeids": nodeids[:limit],
        "truncated": len(nodeids) > limit,
        "returncode": proc.returncode,
        "stderr": (proc.stderr or "")[-2000:],
    }


@router.get("/profiles")
def profiles(request: Request) -> dict[str, Any]:
    path = _config_path(request)
    try:
        names = list_profile_names(path)
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"profiles": names, "path": str(path)}


@router.get("/profiles/{name}")
def get_profile(name: str, request: Request) -> dict[str, Any]:
    try:
        return get_profile_public(_config_path(request), name)
    except AuthoringError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/profiles/{name}/validate")
def validate_profile(name: str, body: ProfileBody, request: Request) -> dict[str, Any]:
    try:
        return validate_profile_patch(
            _config_path(request),
            name,
            body.fields,
            project_root=_project_root(request),
        )
    except AuthoringError as exc:
        return {"ok": False, "errors": [str(exc)], "settings_summary": None}


@router.post("/profiles/{name}")
def save_profile(name: str, body: ProfileBody, request: Request) -> dict[str, Any]:
    try:
        result = preview_and_save_profile(
            _config_path(request),
            name,
            body.fields,
            project_root=_project_root(request),
            apply=body.apply,
        )
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result["ok"]:
        raise HTTPException(status_code=400, detail={"errors": result["errors"]})
    return result


@router.get("/quarantine")
def quarantine_list(request: Request) -> dict[str, Any]:
    from questline.authoring.quarantine import QuarantineLedger

    path = _quarantine_path(request)
    try:
        ledger = QuarantineLedger.load(path)
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "path": str(path),
        "entries": [e.to_dict() for e in ledger.entries()],
    }


@router.post("/quarantine")
def quarantine_add(body: QuarantineAddBody, request: Request) -> dict[str, Any]:
    from questline.authoring.quarantine import QuarantineLedger

    path = _quarantine_path(request)
    try:
        ledger = QuarantineLedger.load(path)
        entry = ledger.add(
            body.test_id,
            reason=body.reason,
            owner=body.owner,
            exit_criteria=body.exit_criteria,
            issue=body.issue,
            feature=body.feature,
        )
        ledger.save()
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"entry": entry.to_dict(), "path": str(path)}


@router.delete("/quarantine")
def quarantine_remove(
    request: Request,
    test_id: str = Query(..., description="Pytest nodeid"),
) -> dict[str, Any]:
    from questline.authoring.quarantine import QuarantineLedger

    path = _quarantine_path(request)
    try:
        ledger = QuarantineLedger.load(path)
        if not ledger.remove(test_id):
            raise HTTPException(status_code=404, detail=f"no entry for {test_id}")
        ledger.save()
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"removed": test_id, "path": str(path)}


@router.post("/quarantine/audit")
def quarantine_audit(body: QuarantineAuditBody, request: Request) -> dict[str, Any]:
    from questline.authoring.quarantine import QuarantineLedger, collect_quarantined_nodeids

    path = _quarantine_path(request)
    root = Path(body.rootdir) if body.rootdir else _project_root(request)
    # Scope collection to the HUD project root by default (avoid ambient cwd suites).
    testpaths = body.tests if body.tests is not None else [str(root)]
    try:
        ledger = QuarantineLedger.load(path)
        marked = collect_quarantined_nodeids(testpaths, rootdir=root)
        report = ledger.audit(marked)
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": report.ok,
        "ledger_only": report.ledger_only,
        "marker_only": report.marker_only,
        "summary": report.summary(),
    }


@router.post("/launcher/start")
def runs_launch(body: LaunchBody, request: Request) -> dict[str, Any]:
    launcher = _launcher(request)
    req = LaunchRequest(
        profile=body.profile,
        tests=list(body.tests),
        markers=body.markers,
        device_serial=body.device_serial,
        reporters=body.reporters,
        include_quarantined=body.include_quarantined,
        config_path=_config_path(request),
        cwd=_project_root(request),
    )
    try:
        status = launcher.launch(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DeviceError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"launcher": status.to_dict()}


@router.get("/launcher")
def runs_launcher_status(request: Request) -> dict[str, Any]:
    return {"launcher": _launcher(request).status().to_dict()}


@router.post("/launcher/stop")
def runs_launcher_stop(request: Request) -> dict[str, Any]:
    return {"launcher": _launcher(request).stop().to_dict()}


@router.get("/perf/compare")
def perf_compare(
    request: Request,
    a: str = Query(..., description="Run id A (baseline)"),
    b: str = Query(..., description="Run id B (candidate)"),
) -> dict[str, Any]:
    store = getattr(_state(request), "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="run store not configured")
    data = compare_perf_runs(store, a, b)
    if not data["found_a"]:
        raise HTTPException(status_code=404, detail=f"run not found: {a}")
    if not data["found_b"]:
        raise HTTPException(status_code=404, detail=f"run not found: {b}")
    return data


@router.get("/perf/correlation")
def perf_correlation(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    store = getattr(_state(request), "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="run store not configured")
    return {"tests": duration_pass_correlation(store, limit=limit)}


@router.get("/perf/{run_id}")
def perf_run(
    run_id: str,
    request: Request,
    test_id: str | None = None,
    metric: str | None = None,
) -> dict[str, Any]:
    store = getattr(_state(request), "store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="run store not configured")
    data = perf_series_for_run(store, run_id, test_id=test_id, metric=metric)
    if not data["found"]:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")
    # Drop raw sample dump size for default response — series is enough for graphs.
    data.pop("samples", None)
    return data
