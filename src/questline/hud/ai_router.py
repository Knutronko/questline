"""HUD LLM router builder — no questline.ai.factory / cursor_cli imports."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Request

from questline.core.errors import AuthoringError
from questline.core.store import RunStore


def build_hud_router(
    request: Request, store: RunStore, profile: str | None, *, run_id: str
) -> Any:
    """Build a ProviderRouter without importing ``questline.ai.factory``."""
    injected = getattr(request.app.state, "llm_provider", None)
    if injected is not None:
        from questline.ai.router import ProviderRouter

        return ProviderRouter(
            [injected],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id=run_id,
        )

    from questline.ai.pricing import load_pricing
    from questline.ai.providers.fake import FakeProvider
    from questline.ai.providers.ollama import OllamaProvider
    from questline.ai.providers.openai_compat import OpenAICompatProvider
    from questline.ai.router import ProviderRouter
    from questline.core.config import load_settings

    cfg = getattr(request.app.state, "config_path", None)
    root = getattr(request.app.state, "project_root", None)
    name = (profile or "").strip() or "ai_groq"
    try:
        settings = load_settings(
            config_path=cfg,
            profile=name,
            project_root=root,
        )
    except AuthoringError:
        return None
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
        store=store,
        run_id=run_id,
        pricing=load_pricing(),
        models=dict(settings.ai.models),
    )
