"""Map AltTester / WebSocket failures onto the Questline error taxonomy."""

from __future__ import annotations

from questline.core.errors import (
    AuthoringError,
    ElementNotFoundError,
    InfraError,
    QuestlineError,
    SessionLostError,
)

# AltTester WebSocket close codes (alttester._websocket).
_CLOSE_NO_APP = 4001
_CLOSE_APP_DISCONNECTED = 4002


def map_alttester_error(exc: BaseException) -> QuestlineError:
    """Translate an AltTester exception into a QuestlineError (idempotent)."""
    if isinstance(exc, QuestlineError):
        return exc

    name = type(exc).__name__
    message = str(exc) or name
    close_code = _extract_close_code(exc)

    # Explicit close-code mapping (brief: no-app → InfraError, disconnect → SessionLost).
    if close_code == _CLOSE_NO_APP or name in {"NoAppConnected"}:
        return InfraError(f"no app connected to AltTester server: {message}")
    if close_code == _CLOSE_APP_DISCONNECTED or name in {"AppDisconnectedError"}:
        return SessionLostError(
            f"app disconnected from AltTester: {message}",
            kind="app_disconnected",
            close_code=close_code or _CLOSE_APP_DISCONNECTED,
        )

    if name in {
        "NotFoundException",
        "ObjectNotFoundException",
        "WaitTimeOutException",
    }:
        return ElementNotFoundError(message)

    if name in {
        "InvalidPathException",
        "InvalidParameterTypeException",
        "InvalidParameterValueException",
        "FailedToParseArgumentsException",
        "MethodNotFoundException",
        "MethodWithGivenParametersNotFoundException",
        "ComponentNotFoundException",
        "AssemblyNotFoundException",
    }:
        return AuthoringError(message)

    if name in {
        "ConnectionError",
        "ConnectionTimeoutError",
        "MultipleDriverError",
        "MultipleDriversTryingToConnectException",
        "MaxNoOfConnectionsDriversExceededException",
        "CommandResponseTimeoutException",
    }:
        return InfraError(message)

    # Fallback: treat unknown AltTester errors as infra (do not mis-blame the test).
    module = type(exc).__module__ or ""
    if module.startswith("alttester"):
        return InfraError(f"alttester error ({name}): {message}")
    return InfraError(f"unexpected driver transport error ({name}): {message}")


def _extract_close_code(exc: BaseException) -> int | None:
    for attr in ("close_code", "close_status_code", "status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None
