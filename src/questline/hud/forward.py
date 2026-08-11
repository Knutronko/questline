"""Forward EventBus events from a pytest subprocess to the HUD ingest API."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from questline.core.events import Event, EventBus

logger = logging.getLogger("questline.hud.forward")

ENV_URL = "QUESTLINE_HUD_FORWARD_URL"
ENV_CSRF = "QUESTLINE_HUD_CSRF"


class HudEventForwarder:
    """POST event.to_dict() to HUD ``/api/live/ingest`` (best-effort)."""

    def __init__(self, url: str, *, csrf: str | None = None, timeout_s: float = 1.5) -> None:
        self.url = url.rstrip("/")
        self.csrf = csrf
        self.timeout_s = timeout_s

    def __call__(self, event: Event) -> None:
        payload = event.to_dict()
        body = json.dumps(payload, default=str).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.csrf:
            headers["X-CSRF-Token"] = self.csrf
            # Cookie mirroring so middleware csrf_ok passes.
            headers["Cookie"] = f"questline_csrf={self.csrf}"
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                resp.read()
        except (urllib.error.URLError, TimeoutError, OSError):
            logger.debug("HUD forward failed for %s", event.type_name, exc_info=True)


def attach_hud_forwarder(bus: EventBus, *, environ: dict[str, str] | None = None) -> Any:
    """Subscribe a forwarder when QUESTLINE_HUD_FORWARD_URL is set. Returns handler or None."""
    env = environ if environ is not None else dict(os.environ)
    url = (env.get(ENV_URL) or "").strip()
    if not url:
        return None
    csrf = (env.get(ENV_CSRF) or "").strip() or None
    handler = HudEventForwarder(url, csrf=csrf)
    bus.subscribe(handler)
    return handler
