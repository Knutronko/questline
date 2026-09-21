"""Build a ProviderRouter without questline.ai.factory (no cursor_cli import)."""

from __future__ import annotations

import os
from typing import Any

from questline.mcp.context import McpContext


def build_mcp_router(ctx: McpContext, run_id: str) -> Any | None:
    """Same skip rules as HUD: cursor_cli is never loaded from this process."""
    if ctx.llm_provider is not None:
        from questline.ai.router import ProviderRouter

        return ProviderRouter(
            [ctx.llm_provider],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=ctx.store,
            run_id=run_id,
        )

    from questline.ai.pricing import load_pricing
    from questline.ai.providers.fake import FakeProvider
    from questline.ai.providers.ollama import OllamaProvider
    from questline.ai.providers.openai_compat import OpenAICompatProvider
    from questline.ai.router import ProviderRouter

    settings = ctx.settings
    env = dict(os.environ)
    providers: list[Any] = []
    names = list(settings.ai.candidates) or list(settings.ai.providers)
    for item in names:
        spec = settings.ai.providers.get(item)
        if spec is None:
            continue
        kind = spec.kind.strip().lower()
        if kind == "cursor_cli":
            continue
        if kind == "ollama":
            providers.append(
                OllamaProvider(
                    name=item,
                    base_url=spec.base_url or "http://127.0.0.1:11434",
                    model=spec.model or "llama3.2",
                    timeout_s=spec.timeout_s,
                )
            )
            continue
        if kind == "fake":
            providers.append(FakeProvider(name=item, model=spec.model or "fake-test"))
            continue
        if kind == "openai_compat":
            key_name = spec.api_key_env or ""
            if not key_name or not (env.get(key_name) or "").strip():
                continue
            if not spec.base_url or not spec.model:
                continue
            providers.append(
                OpenAICompatProvider(
                    name=item,
                    base_url=spec.base_url,
                    model=spec.model,
                    api_key_env=key_name,
                    environ=env,
                    timeout_s=spec.timeout_s,
                )
            )
    if not providers:
        return None
    return ProviderRouter(
        providers,
        budget_per_call_usd=settings.ai.budget_per_call_usd,
        budget_per_run_usd=settings.ai.budget_per_run_usd,
        store=ctx.store,
        run_id=run_id,
        pricing=load_pricing(),
        models=dict(settings.ai.models),
    )
