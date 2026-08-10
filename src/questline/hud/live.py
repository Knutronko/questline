"""WebSocket live bridge: EventBus → connected HUD clients."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from questline.core.events import Event, EventBus

logger = logging.getLogger("questline.hud.live")


class LiveBridge:
    """Fan-out bus events to WebSocket subscribers (asyncio-safe)."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus
        self._clients: set[Any] = set()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._attached = False

    def attach(self, bus: EventBus) -> None:
        if self._attached and self._bus is bus:
            return
        if self._bus is not None and self._attached:
            self._bus.unsubscribe(self._on_event)
        self._bus = bus
        bus.subscribe(self._on_event)
        self._attached = True

    def detach(self) -> None:
        if self._bus is not None and self._attached:
            self._bus.unsubscribe(self._on_event)
        self._attached = False

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def register(self, websocket: Any) -> None:
        self._clients.add(websocket)
        try:
            await websocket.send_json({"type": "hello", "clients": len(self._clients)})
            while True:
                # Keep the connection open; clients may send pings (ignored).
                msg = await websocket.receive_text()
                if msg in {"close", "bye"}:
                    break
        finally:
            self._clients.discard(websocket)

    def _on_event(self, event: Event) -> None:
        if not self._clients:
            return
        payload = event.to_dict()
        loop = self._loop
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.debug("live bridge: no event loop; drop %s", event.type_name)
                return
        for client in list(self._clients):
            try:
                asyncio.run_coroutine_threadsafe(self._safe_send(client, payload), loop)
            except Exception:
                logger.exception("live bridge schedule failed")

    async def _safe_send(self, client: Any, payload: dict[str, Any]) -> None:
        try:
            await client.send_json(payload)
        except Exception:
            self._clients.discard(client)
            logger.debug("live client dropped", exc_info=True)
