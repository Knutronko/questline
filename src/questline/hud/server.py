"""FastAPI application factory for the Questline HUD."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from questline.core.events import EventBus
from questline.core.store import RunStore
from questline.hud import static_dir
from questline.hud.api import router as api_router
from questline.hud.live import LiveBridge

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
) -> FastAPI:
    """Build the HUD app bound to *store* (and optional live *bus*)."""
    app = FastAPI(title="Questline HUD", docs_url=None, redoc_url=None)
    app.state.store = store
    bridge = LiveBridge(bus)
    if bus is not None:
        bridge.attach(bus)
    app.state.live = bridge
    app.state.bus = bus

    app.include_router(api_router)

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
            # Do not steal API / live routes (already registered).
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
) -> None:  # pragma: no cover — blocks on uvicorn; CLI unit-tests mock this
    """Block and serve the HUD (uvicorn)."""
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "HUD requires the optional extra: pip install 'questline[hud]'"
        ) from exc

    app = create_app(store=store, bus=bus)
    if open_browser:
        import threading
        import webbrowser

        def _open() -> None:
            webbrowser.open(f"http://{host}:{port}/")

        threading.Timer(0.6, _open).start()

    logger.info("HUD listening on http://%s:%s/", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")
