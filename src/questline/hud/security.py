"""Localhost + CSRF guards for HUD mutating APIs (phase-10)."""

from __future__ import annotations

import secrets
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

CSRF_COOKIE = "questline_csrf"
CSRF_HEADER = "x-csrf-token"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    h = host.strip().lower().split("%", 1)[0]
    if h in _LOCAL_HOSTS:
        return True
    # IPv4-mapped IPv6 (::ffff:127.0.0.1)
    if h.startswith("::ffff:") and h.removeprefix("::ffff:") in _LOCAL_HOSTS:
        return True
    return False


def client_is_localhost(request: Request) -> bool:
    client = request.client
    if client is not None and is_loopback_host(client.host):
        return True
    # Some ASGI servers put the peer in scope only.
    peer = request.scope.get("client")
    if isinstance(peer, (list, tuple)) and peer:
        return is_loopback_host(str(peer[0]))
    return False


def csrf_ok(request: Request) -> bool:
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header:
        return False
    return secrets.compare_digest(cookie, header)


class HudSecurityMiddleware(BaseHTTPMiddleware):
    """Reject mutating /api requests when read-only, remote, or CSRF missing."""

    def __init__(self, app: Any, *, read_only: bool = False) -> None:
        super().__init__(app)
        self.read_only = read_only

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        method = request.method.upper()
        mutating = method not in _SAFE_METHODS
        is_api = path.startswith("/api/")

        if mutating and is_api:
            if self.read_only:
                return JSONResponse(
                    {"detail": "HUD is in --read-only mode; mutating APIs disabled"},
                    status_code=403,
                )
            if not client_is_localhost(request):
                return JSONResponse(
                    {"detail": "mutating HUD APIs are localhost-only"},
                    status_code=403,
                )
            # CSRF bootstrap endpoint is itself a GET; mutators need token.
            if path != "/api/csrf" and not csrf_ok(request):
                return JSONResponse(
                    {
                        "detail": (
                            f"CSRF required: GET /api/csrf then send cookie "
                            f"{CSRF_COOKIE} matching header {CSRF_HEADER}"
                        )
                    },
                    status_code=403,
                )

        return await call_next(request)
