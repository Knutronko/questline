"""1-token provider pings for ``questline doctor`` (no secret values)."""

from __future__ import annotations

from dataclasses import dataclass

from questline.ai.factory import build_named_provider, provider_statuses
from questline.ai.port import LlmMessage, LlmRequest
from questline.ai.pricing import load_pricing
from questline.ai.router import ProviderRouter
from questline.core.config import Settings
from questline.core.errors import AuthoringError
from questline.core.events import EventBus
from questline.core.store import RunStore


@dataclass(frozen=True, slots=True)
class PingResult:
    name: str
    usable: bool
    detail: str


def ping_providers(
    settings: Settings,
    *,
    store: RunStore | None = None,
    bus: EventBus | None = None,
    environ: dict[str, str] | None = None,
) -> list[PingResult]:
    statuses = provider_statuses(settings, environ=environ)
    out: list[PingResult] = []
    for st in statuses:
        if not st.usable:
            out.append(PingResult(st.name, False, st.detail))
            continue
        try:
            provider = build_named_provider(settings, st.name, environ=environ)
        except AuthoringError as exc:
            out.append(PingResult(st.name, False, str(exc)))
            continue
        router = ProviderRouter(
            [provider],
            budget_per_call_usd=max(settings.ai.budget_per_call_usd, 0.5),
            budget_per_run_usd=max(settings.ai.budget_per_run_usd, 1.0),
            store=store,
            bus=bus,
            run_id="doctor",
            pricing=load_pricing(),
            models=dict(settings.ai.models),
        )
        try:
            resp = router.complete(
                LlmRequest(
                    messages=(
                        LlmMessage(role="user", content="Reply with the single character y."),
                    ),
                    max_tokens=1,
                    temperature=0.0,
                    purpose_tag="doctor.ping",
                )
            )
            preview = (resp.text or "").replace("\n", " ").strip()[:40]
            out.append(PingResult(st.name, True, f"ok model={resp.model} {preview!r}"))
        except Exception as exc:
            out.append(PingResult(st.name, False, f"{type(exc).__name__}: {exc}"))
    return out
