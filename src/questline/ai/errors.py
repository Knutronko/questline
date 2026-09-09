"""LLMPort errors — budget is a hard stop, never a warning."""

from __future__ import annotations

from questline.core.errors import ProviderError, QuestlineError


class RateLimitedError(ProviderError):
    """Provider returned HTTP 429 (or equivalent). Router may fall back."""

    def __init__(
        self,
        message: str = "rate limited",
        *,
        retry_after_s: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class BudgetExceededError(QuestlineError):
    """Per-call or per-run USD ceiling hit. Hard stop — do not continue the task."""

    def __init__(
        self,
        message: str = "AI budget exceeded",
        *,
        spent_usd: float = 0.0,
        ceiling_usd: float = 0.0,
        kind: str = "run",
    ) -> None:
        super().__init__(message)
        self.spent_usd = spent_usd
        self.ceiling_usd = ceiling_usd
        self.kind = kind
