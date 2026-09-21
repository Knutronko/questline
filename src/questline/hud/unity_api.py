"""HUD Unity CLI chip: status + Ensure Editor. Same functions as the CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from questline.core.config import load_settings
from questline.core.errors import AuthoringError
from questline.unity_cli.client import UnityCli
from questline.unity_cli.ensure import ensure_editor
from questline.unity_cli.status import probe_status

router = APIRouter(prefix="/api")


class EnsureEditorBody(BaseModel):
    profile: str | None = None
    config: str | None = None


def _project_root(request: Request) -> Path:
    root = getattr(request.app.state, "project_root", None)
    if root is not None:
        return Path(root)
    cfg = getattr(request.app.state, "config_path", None)
    return Path(cfg).parent if cfg else Path.cwd()


def _config_path(request: Request, config: str | None) -> Path:
    root = _project_root(request).resolve()
    default = getattr(request.app.state, "config_path", None)
    if not config or not str(config).strip():
        return Path(default).resolve() if default else (root / "questline.toml")
    raw = Path(config.strip())
    path = raw if raw.is_absolute() else (root / raw)
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="config path outside project root") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="config not found")
    return path


def _settings(request: Request, profile: str | None, config: str | None) -> Any:
    path = _config_path(request, config)
    try:
        return load_settings(
            config_path=path if path.is_file() else None,
            profile=profile,
            project_root=_project_root(request),
        )
    except AuthoringError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _cli(request: Request) -> UnityCli:
    which = getattr(request.app.state, "unity_which", None)
    runner = getattr(request.app.state, "unity_runner", None)
    kwargs: dict[str, Any] = {}
    if which is not None:
        kwargs["which"] = which
    if runner is not None:
        kwargs["runner"] = runner
    return UnityCli(**kwargs)


@router.get("/unity/status")
def unity_status(
    request: Request,
    profile: str | None = None,
    config: str | None = Query(default=None),
) -> dict[str, Any]:
    settings = _settings(request, profile, config)
    status = probe_status(settings, cli=_cli(request))
    return {"unity": status.to_public()}


@router.post("/unity/ensure-editor")
def unity_ensure_editor(request: Request, body: EnsureEditorBody | None = None) -> dict[str, Any]:
    payload = body or EnsureEditorBody()
    settings = _settings(request, payload.profile, payload.config)
    waiter = getattr(request.app.state, "unity_wait", None)
    result = ensure_editor(settings, cli=_cli(request), wait_wire=waiter)
    return result.to_public()
