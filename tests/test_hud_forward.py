"""Unit coverage for HUD event forwarder (pytest → ingest)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from questline.core.events import EventBus, RunStarted
from questline.hud.forward import HudEventForwarder, attach_hud_forwarder


def test_attach_noop_without_env() -> None:
    bus = EventBus()
    assert attach_hud_forwarder(bus, environ={}) is None


def test_forwarder_posts_json() -> None:
    handler = HudEventForwarder("http://127.0.0.1:8741/api/live/ingest", csrf="tok")
    with patch("questline.hud.forward.urllib.request.urlopen") as urlopen:
        resp = MagicMock()
        resp.read.return_value = b'{"status":"ok"}'
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        urlopen.return_value = resp
        handler(
            RunStarted(
                run_id="r1",
                profile="mock",
                timestamp=datetime(2026, 8, 11, tzinfo=UTC),
            )
        )
        assert urlopen.called
        req = urlopen.call_args[0][0]
        assert req.get_method() == "POST"
        assert "questline_csrf=tok" in req.headers.get("Cookie", "")


def test_attach_subscribes() -> None:
    bus = EventBus()
    handler = attach_hud_forwarder(
        bus,
        environ={
            "QUESTLINE_HUD_FORWARD_URL": "http://127.0.0.1:9/api/live/ingest",
            "QUESTLINE_HUD_CSRF": "x",
        },
    )
    assert handler is not None
