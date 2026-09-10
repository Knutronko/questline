"""ProviderRouter: ordered fallback + hard USD budget caps."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import replace

from questline.ai.errors import BudgetExceededError, RateLimitedError
from questline.ai.ledger import record_ai_call
from questline.ai.port import LLMProvider, LlmRequest, LlmResponse, TokenUsage
from questline.ai.pricing import PRICING_VERSION, PricingTable, load_pricing
from questline.core.errors import ProviderError
from questline.core.events import EventBus
from questline.core.store import RunStore

_RETRYABLE = (RateLimitedError, ProviderError, TimeoutError)


class ProviderRouter:
    """Try candidates in order. Every attempt is ledgered. Budget is a hard stop."""

    def __init__(
        self,
        providers: Sequence[LLMProvider],
        *,
        budget_per_call_usd: float,
        budget_per_run_usd: float,
        store: RunStore | None = None,
        bus: EventBus | None = None,
        run_id: str = "",
        pricing: PricingTable | None = None,
        models: dict[str, str] | None = None,
    ) -> None:
        if not providers:
            raise ProviderError("ProviderRouter requires at least one provider")
        if budget_per_call_usd < 0 or budget_per_run_usd < 0:
            raise ProviderError("AI budget ceilings must be >= 0")
        self._providers = list(providers)
        self._budget_per_call = float(budget_per_call_usd)
        self._budget_per_run = float(budget_per_run_usd)
        self._store = store
        self._bus = bus
        self._run_id = run_id
        self._pricing = pricing or load_pricing()
        self._models = dict(models or {})
        self._spent = 0.0

    @property
    def spent_usd(self) -> float:
        return self._spent

    def complete(self, req: LlmRequest) -> LlmResponse:
        if self._spent > self._budget_per_run:
            raise BudgetExceededError(
                f"AI per-run budget exceeded: spent {self._spent:.6f} > "
                f"ceiling {self._budget_per_run:.6f} USD",
                spent_usd=self._spent,
                ceiling_usd=self._budget_per_run,
                kind="run",
            )

        errors: list[str] = []
        last_exc: BaseException | None = None

        for index, provider in enumerate(self._providers):
            call_req = self._bind_model(provider, req, primary=index == 0)
            started = time.perf_counter()
            try:
                response = provider.complete(call_req)
            except _RETRYABLE as exc:
                duration_ms = (time.perf_counter() - started) * 1000.0
                outcome = "rate_limited" if isinstance(exc, RateLimitedError) else "error"
                self._ledger_failure(provider, call_req, duration_ms, outcome)
                errors.append(f"{provider.name}: {exc}")
                last_exc = exc
                continue
            except BudgetExceededError:
                raise
            except Exception as exc:
                duration_ms = (time.perf_counter() - started) * 1000.0
                self._ledger_failure(provider, call_req, duration_ms, "error")
                errors.append(f"{provider.name}: {exc}")
                last_exc = exc
                continue

            duration_ms = response.duration_ms or (time.perf_counter() - started) * 1000.0
            usage = response.usage or TokenUsage()
            cost = self._pricing.estimate(
                model=response.model or provider.model,
                kind=provider.kind,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cached=usage.cached,
                cached_tokens=usage.cached_tokens,
            )
            record_ai_call(
                store=self._store,
                bus=self._bus,
                run_id=self._run_id,
                provider=provider.name,
                model=response.model or provider.model,
                tokens_in=usage.tokens_in,
                tokens_out=usage.tokens_out,
                cost=cost,
                purpose=call_req.purpose_tag,
                duration_ms=duration_ms,
                cached=usage.cached,
                outcome="ok",
                pricing_version=self._pricing.version or PRICING_VERSION,
            )
            if cost > self._budget_per_call:
                self._spent += cost
                raise BudgetExceededError(
                    f"AI per-call budget exceeded: cost {cost:.6f} > "
                    f"ceiling {self._budget_per_call:.6f} USD",
                    spent_usd=cost,
                    ceiling_usd=self._budget_per_call,
                    kind="call",
                )
            self._spent += cost
            if self._spent > self._budget_per_run:
                raise BudgetExceededError(
                    f"AI per-run budget exceeded: spent {self._spent:.6f} > "
                    f"ceiling {self._budget_per_run:.6f} USD",
                    spent_usd=self._spent,
                    ceiling_usd=self._budget_per_run,
                    kind="run",
                )
            return replace(
                response,
                duration_ms=duration_ms,
                provider=response.provider or provider.name,
                model=response.model or provider.model,
            )

        detail = "; ".join(errors) or "no providers"
        raise ProviderError(f"all LLM providers failed ({detail})") from last_exc

    def _bind_model(self, provider: LLMProvider, req: LlmRequest, *, primary: bool) -> LlmRequest:
        """Caller pin wins. Else primary uses models.fast|strong; fallbacks keep vendor id."""
        if req.model:
            return req
        mapped = self._models.get(req.model_class) or self._models.get("fast")
        if primary and mapped:
            return replace(req, model=mapped)
        if provider.model:
            return replace(req, model=provider.model)
        if mapped:
            return replace(req, model=mapped)
        return req

    def _ledger_failure(
        self,
        provider: LLMProvider,
        req: LlmRequest,
        duration_ms: float,
        outcome: str,
    ) -> None:
        record_ai_call(
            store=self._store,
            bus=self._bus,
            run_id=self._run_id,
            provider=provider.name,
            model=req.model or provider.model,
            tokens_in=0,
            tokens_out=0,
            cost=0.0,
            purpose=req.purpose_tag,
            duration_ms=duration_ms,
            cached=False,
            outcome=outcome,
            pricing_version=self._pricing.version or PRICING_VERSION,
        )
