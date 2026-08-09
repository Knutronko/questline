"""Error taxonomy and verdict classification (architecture §2.4)."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal


class Verdict(StrEnum):
    """Failure classification persisted in the run store."""

    INFRA = "infra"
    TEST = "test"
    AUTHORING = "authoring"
    UNKNOWN = "unknown"


TimeoutKind = Literal["probe", "deadline"]


class QuestlineError(Exception):
    """Base for all framework-raised errors."""

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class InfraError(QuestlineError):
    """Driver/device/broker/network — not the test's fault."""


class SessionLostError(InfraError):
    def __init__(
        self,
        message: str = "session lost",
        *,
        kind: str = "unknown",
        close_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.close_code = close_code


class DeviceError(InfraError):
    """Device provider or adb/farm failure."""


class ProviderError(InfraError):
    """External provider (LLM, farm, CI) failure."""


class TestError(QuestlineError):
    """The test or the game contradicts expectations."""

    __test__ = False  # not a pytest test class


class ElementNotFoundError(TestError):
    """Required element was not found within the wait policy."""


class AssertionFailedError(TestError):
    """An assertion did not hold."""


class TimeoutExceededError(TestError):
    def __init__(
        self,
        message: str = "timeout exceeded",
        *,
        kind: TimeoutKind = "deadline",
    ) -> None:
        super().__init__(message)
        self.kind = kind


class AuthoringError(QuestlineError):
    """Malformed test code — fails fast at collection/build time."""


# (type_name or None for any, message regex or None for any-type match, kind)
# First match wins. Type-only rows match that exception class regardless of message.
_SESSION_LOST_SIGNATURES: tuple[tuple[str | None, re.Pattern[str] | None, str], ...] = (
    ("ConnectionResetError", None, "disconnect"),
    ("ConnectionRefusedError", None, "disconnect"),
    ("BrokenPipeError", None, "disconnect"),
    ("ConnectionAbortedError", None, "disconnect"),
    ("ConnectionError", None, "disconnect"),
    ("TimeoutError", re.compile(r"connect|read|socket|wire|alttester", re.I), "timeout"),
    ("OSError", re.compile(r"connection (closed|reset|refused|aborted)", re.I), "disconnect"),
    (None, re.compile(r"connection closed", re.I), "disconnect"),
    (None, re.compile(r"connection reset", re.I), "disconnect"),
    (None, re.compile(r"broken pipe", re.I), "disconnect"),
    (None, re.compile(r"no app connected", re.I), "no_app"),
    (None, re.compile(r"app disconnected", re.I), "app_disconnected"),
    (None, re.compile(r"empty hierarchy", re.I), "empty_hierarchy"),
    (None, re.compile(r"session (lost|dropped|closed)", re.I), "disconnect"),
    (None, re.compile(r"wire connection (closed|lost)", re.I), "disconnect"),
    (None, re.compile(r"websocket.*(closed|disconnect)", re.I), "disconnect"),
)


def normalize_exception(exc: BaseException) -> BaseException:
    """Wrap known transport / signature failures as ``SessionLostError``.

    Already-classified ``QuestlineError`` instances are returned unchanged.
    Bare ``AssertionError`` is left as-is so ``classify`` maps it to ``TEST``.
    """
    if isinstance(exc, QuestlineError):
        return exc

    type_name = type(exc).__name__
    message = str(exc) or type_name
    close_code = _extract_close_code(exc)

    for type_pat, msg_pat, kind in _SESSION_LOST_SIGNATURES:
        if type_pat is not None and type_name != type_pat:
            continue
        if msg_pat is not None and not msg_pat.search(message):
            continue
        return SessionLostError(message, kind=kind, close_code=close_code)

    return exc


def classify(exc: BaseException) -> Verdict:
    """Map an exception to a store/reporter verdict.

    Transport signatures are normalized to ``SessionLostError`` first so
    reporters always see ``verdict=infra`` for session loss. Bare
    ``AssertionError`` maps to ``test`` (not unknown).
    """
    normalized = normalize_exception(exc)
    if isinstance(normalized, AuthoringError):
        return Verdict.AUTHORING
    if isinstance(normalized, InfraError):
        return Verdict.INFRA
    if isinstance(normalized, TestError):
        return Verdict.TEST
    if isinstance(normalized, AssertionError):
        return Verdict.TEST
    if isinstance(normalized, QuestlineError):
        return Verdict.UNKNOWN
    return Verdict.UNKNOWN


def _extract_close_code(exc: BaseException) -> int | None:
    for attr in ("close_code", "close_status_code", "status_code", "code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None
