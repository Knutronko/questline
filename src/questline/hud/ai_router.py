"""HUD LLM router builder — no questline.ai.factory / cursor_cli imports."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Request

from questline.core.errors import AuthoringError
from questline.core.store import RunStore

_GROQ_BASE = "https://api.groq.com/openai/v1"
_GROQ_MODEL = "openai/gpt-oss-20b"
_GROQ_KEY_ENV = "GROQ_API_KEY"


def build_hud_router(
    request: Request, store: RunStore, profile: str | None, *, run_id: str
) -> Any:
    """Build a ProviderRouter without importing ``questline.ai.factory``.

    Game-suite ``questline.toml`` often has only ``editor`` / ``android_local``.
    Missing ``ai_groq`` must not silently disable live Generate: if
    ``GROQ_API_KEY`` is in the HUD process env, use Groq defaults.
    """
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
    from questline.ai.router import ProviderRouter

    env = dict(os.environ)
    cfg = getattr(request.app.state, "config_path", None)
    root = getattr(request.app.state, "project_root", None)
    name = (profile or "").strip() or "ai_groq"
    settings = _load_ai_settings(cfg, root, name)
    providers = _providers_from_settings(settings, env)
    if not providers:
        groq = _env_groq_provider(env)
        if groq is not None:
            providers = [groq]
    providers = _with_ollama_fallback(providers)
    if not providers:
        return None
    budget_call = 0.05
    budget_run = 1.0
    models: dict[str, str] = {}
    if settings is not None:
        budget_call = settings.ai.budget_per_call_usd
        budget_run = settings.ai.budget_per_run_usd
        models = dict(settings.ai.models)
    return ProviderRouter(
        providers,
        budget_per_call_usd=budget_call,
        budget_per_run_usd=budget_run,
        store=store,
        run_id=run_id,
        pricing=load_pricing(),
        models=models,
    )


def hud_has_llm(request: Request, store: RunStore | None) -> bool:
    if store is None:
        return False
    return build_hud_router(request, store, None, run_id="hud-meta") is not None


def _load_ai_settings(cfg: Any, root: Any, name: str) -> Any | None:
    from questline.core.config import load_settings

    try:
        return load_settings(config_path=cfg, profile=name, project_root=root)
    except AuthoringError:
        pass
    try:
        return load_settings(config_path=cfg, profile=None, project_root=root)
    except AuthoringError:
        return None


def _providers_from_settings(settings: Any, env: dict[str, str]) -> list[Any]:
    if settings is None:
        return []
    from questline.ai.providers.fake import FakeProvider
    from questline.ai.providers.ollama import OllamaProvider
    from questline.ai.providers.openai_compat import OpenAICompatProvider

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
    return providers


def _env_groq_provider(env: dict[str, str]) -> Any | None:
    if not (env.get(_GROQ_KEY_ENV) or "").strip():
        return None
    from questline.ai.providers.openai_compat import OpenAICompatProvider

    return OpenAICompatProvider(
        name="groq",
        base_url=_GROQ_BASE,
        model=_GROQ_MODEL,
        api_key_env=_GROQ_KEY_ENV,
        environ=env,
        timeout_s=60.0,
    )


def _with_ollama_fallback(providers: list[Any]) -> list[Any]:
    """After Groq 429, try local Ollama. Skip if the list is empty or already has it."""
    if not providers:
        return providers
    if any(getattr(p, "name", "") == "ollama" for p in providers):
        return providers
    from questline.ai.providers.ollama import OllamaProvider

    providers.append(OllamaProvider(name="ollama", timeout_s=60.0))
    return providers
