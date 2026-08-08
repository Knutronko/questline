"""Map QuestlineWire transport / server errors onto the taxonomy."""

from __future__ import annotations

from questline.core.errors import (
    AuthoringError,
    InfraError,
    QuestlineError,
    SessionLostError,
    TestError,
)


def map_wire_error(exc: BaseException) -> QuestlineError:
    """Translate a Wire/socket failure into a QuestlineError (idempotent)."""
    if isinstance(exc, QuestlineError):
        return exc
    name = type(exc).__name__
    message = str(exc) or name
    if name in {"TimeoutError", "socket.timeout"} or isinstance(exc, TimeoutError):
        return SessionLostError(f"wire connect/read timeout: {message}", kind="timeout")
    if name in {"ConnectionRefusedError", "ConnectionResetError", "BrokenPipeError"}:
        return SessionLostError(f"wire connection lost: {message}", kind="disconnect")
    if isinstance(exc, OSError):
        return InfraError(f"wire OS error ({name}): {message}")
    if isinstance(exc, (json_decode_error(), ValueError)):
        return AuthoringError(f"wire protocol error: {message}")
    return InfraError(f"unexpected wire error ({name}): {message}")


def json_decode_error() -> type[BaseException]:
    import json

    return json.JSONDecodeError


def error_from_server(code: str, message: str) -> QuestlineError:
    """Map server ``error.code`` to taxonomy."""
    normalized = (code or "").lower()
    if normalized in {"authoring", "bad_request", "unknown_op", "unknown_hook"}:
        return AuthoringError(message)
    if normalized in {"test", "hook_failed"}:
        return TestError(message)
    if normalized in {"session_lost", "disconnect"}:
        return SessionLostError(message, kind=normalized)
    if normalized in {"infra", "timeout"}:
        return InfraError(message) if normalized == "infra" else SessionLostError(
            message, kind="timeout"
        )
    return InfraError(f"wire server error ({code}): {message}")


_MVP_UI_MSG = (
    "QuestlineWire MVP does not implement UI automation "
    "(find/hierarchy/tap/screenshot). Use call_game_method / hooks, "
    "or phase-14 Poco / AltTesterDriver for hierarchy."
)


def mvp_ui_not_implemented() -> AuthoringError:
    return AuthoringError(_MVP_UI_MSG)
