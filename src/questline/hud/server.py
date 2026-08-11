"""FastAPI application factory for the Questline HUD."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from questline.core.events import EventBus
from questline.core.store import RunStore
from questline.hud import static_dir
from questline.hud.api import router as api_router
from questline.hud.control import router as control_router
from questline.hud.launcher import RunLauncher
from questline.hud.live import LiveBridge
from questline.hud.security import HudSecurityMiddleware, new_csrf_token

logger = logging.getLogger("questline.hud")

_EMPTY_SHELL = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Questline HUD</title>
<style>
 body{font-family:ui-monospace,Consolas,monospace;background:#0b1016;color:#c9d4e0;
  display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
 .box{border:1px solid #2a3544;padding:2rem;max-width:36rem}
 a{color:#6cb6ff}
</style></head>
<body><div class="box">
<h1>Questline HUD</h1>
<p>SPA assets are missing. From the repo root:</p>
<pre>cd hud/frontend
npm ci
npm run build</pre>
<p>Then restart <code>questline hud</code>. See <a href="https://github.com/Knutronko/questline/blob/main/docs/hud.md">docs/hud.md</a>.</p>
</div></body></html>
"""


def create_app(
    *,
    store: RunStore,
    bus: EventBus | None = None,
    static: Path | None = None,
    read_only: bool = False,
    project_root: Path | None = None,
    config_path: Path | None = None,
    quarantine_path: Path | None = None,
    launcher: RunLauncher | None = None,
    forward_base_url: str | None = None,
) -> FastAPI:
    """Build the HUD app bound to *store* (and optional live *bus*).

    When *read_only* is True, mutating control APIs return 403 (phase-08 viewer mode
    for non-localhost / remote viewing).
    """
    app = FastAPI(title="Questline HUD", docs_url=None, redoc_url=None)
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    cfg = Path(config_path) if config_path else root / "questline.toml"
    qpath = Path(quarantine_path) if quarantine_path else root / "quarantine.yaml"

    app.state.store = store
    app.state.read_only = read_only
    app.state.project_root = root
    app.state.config_path = cfg
    app.state.quarantine_path = qpath

    bridge = LiveBridge(bus)
    if bus is not None:
        bridge.attach(bus)
    app.state.live = bridge
    app.state.bus = bus

    csrf_seed = new_csrf_token()
    app.state.csrf_seed = csrf_seed
    if launcher is not None:
        app.state.launcher = launcher
    elif not read_only:
        fwd = (forward_base_url or "http://127.0.0.1:8741").rstrip("/") + "/api/live/ingest"
        app.state.launcher = RunLauncher(
            project_root=root,
            config_path=cfg,
            forward_url=fwd,
            csrf_token=csrf_seed,
            lock_dir=root / ".questline" / "device-locks",
        )
        # Keep launcher CSRF in sync with cookie issued later via /api/csrf when possible.
        # Initial seed lets subprocess forward before the SPA fetches a cookie.
    else:
        app.state.launcher = None

    app.add_middleware(HudSecurityMiddleware, read_only=read_only)
    app.include_router(api_router)
    app.include_router(control_router)

    @app.websocket("/api/live")
    async def live_ws(websocket: WebSocket) -> None:
        import asyncio

        await websocket.accept()
        bridge.bind_loop(asyncio.get_running_loop())
        await bridge.register(websocket)

    # Alias matching the phase brief path.
    @app.websocket("/live")
    async def live_ws_alias(websocket: WebSocket) -> None:
        import asyncio

        await websocket.accept()
        bridge.bind_loop(asyncio.get_running_loop())
        await bridge.register(websocket)

    assets = Path(static) if static is not None else static_dir()
    app.state.static_dir = assets
    index = assets / "index.html"

    if assets.is_dir() and any(assets.iterdir()):
        # Mount hashed assets (JS/CSS) under /assets when Vite emits that layout.
        assets_sub = assets / "assets"
        if assets_sub.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_sub), name="assets")

        @app.get("/")
        async def spa_index() -> Any:
            if not index.is_file():
                return HTMLResponse(_EMPTY_SHELL, status_code=503)
            return FileResponse(index)

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str) -> Any:
            # Never serve the SPA shell for API / live — return JSON 404 instead of
            # index.html (which breaks fetch().json() with "<!DOCTYPE...").
            if full_path == "api" or full_path.startswith("api/") or full_path == "live":
                return JSONResponse(
                    {"detail": f"API route not found: /{full_path}"},
                    status_code=404,
                )
            candidate = assets / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            if index.is_file():
                return FileResponse(index)
            return HTMLResponse(_EMPTY_SHELL, status_code=503)
    else:

        @app.get("/")
        async def missing_assets() -> HTMLResponse:
            return HTMLResponse(_EMPTY_SHELL, status_code=503)

    return app


def serve(
    *,
    store: RunStore,
    bus: EventBus | None = None,
    host: str = "127.0.0.1",
    port: int = 8741,
    open_browser: bool = False,
    read_only: bool = False,
    project_root: Path | None = None,
    config_path: Path | None = None,
    quarantine_path: Path | None = None,
) -> None:  # pragma: no cover — blocks on uvicorn; CLI unit-tests mock this
    """Block and serve the HUD (uvicorn)."""
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "HUD requires the optional extra: pip install 'questline[hud]'"
        ) from exc

    forward = f"http://{host}:{port}"
    app = create_app(
        store=store,
        bus=bus,
        read_only=read_only,
        project_root=project_root,
        config_path=config_path,
        quarantine_path=quarantine_path,
        forward_base_url=forward,
    )
    # Align launcher CSRF with a stable token the SPA can adopt from /api/csrf;
    # also publish seed on launcher so early forwards work if SPA sets cookie to seed.
    launcher = getattr(app.state, "launcher", None)
    if launcher is not None and hasattr(launcher, "csrf_token"):
        # Prefer the seed already installed; SPA /api/csrf rotates cookie — ingest
        # accepts either cookie match. Subprocess gets updated on each launch via
        # launcher.csrf_token; update it when SPA fetches CSRF (see control.csrf_token).
        pass

    if open_browser:
        import threading
        import webbrowser

        def _open() -> None:
            webbrowser.open(f"http://{host}:{port}/")

        threading.Timer(0.6, _open).start()

    logger.info(
        "HUD listening on http://%s:%s/ (read_only=%s)",
        host,
        port,
        read_only,
    )
    uvicorn.run(app, host=host, port=port, log_level="info")
