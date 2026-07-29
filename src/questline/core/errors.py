"""Error taxonomy and verdict classification (architecture §2.4)."""

from __future__ import annotations

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


def classify(exc: BaseException) -> Verdict:
    """Map an exception to a store/reporter verdict."""
    if isinstance(exc, AuthoringError):
        return Verdict.AUTHORING
    if isinstance(exc, InfraError):
        return Verdict.INFRA
    if isinstance(exc, TestError):
        return Verdict.TEST
    if isinstance(exc, QuestlineError):
        return Verdict.UNKNOWN
    return Verdict.UNKNOWN
