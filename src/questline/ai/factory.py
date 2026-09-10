"""Build a ProviderRouter from resolved Settings (keys from env, never toml)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from questline.ai.http import HttpTransport
from questline.ai.port import LLMProvider
from questline.ai.pricing import load_pricing
from questline.ai.providers.anthropic import AnthropicProvider
from questline.ai.providers.fake import FakeProvider
from questline.ai.providers.ollama import OllamaProvider
from questline.ai.providers.openai_compat import OpenAICompatProvider
from questline.ai.router import ProviderRouter
from questline.core.config import AiProviderSettings, Settings
from questline.core.errors import AuthoringError, ProviderError
from questline.core.events import EventBus
from questline.core.store import RunStore

_KINDS_NEEDING_KEY = frozenset({"openai_compat", "anthropic"})


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    name: str
    kind: str
    model: str
    usable: bool
    detail: str
    api_key_env: str | None = None


def provider_statuses(
    settings: Settings,
    *,
    environ: dict[str, str] | None = None,
) -> list[ProviderStatus]:
    env = environ if environ is not None else dict(os.environ)
    names = list(settings.ai.candidates) or list(settings.ai.providers)
    out: list[ProviderStatus] = []
    for name in names:
        spec = settings.ai.providers.get(name)
        if spec is None:
            out.append(
                ProviderStatus(
                    name=name,
                    kind="?",
                    model="",
                    usable=False,
                    detail="not in ai.providers",
                )
            )
            continue
        out.append(_status_for(name, spec, env))
    return out


def build_router(
    settings: Settings,
    *,
    store: RunStore | None = None,
    bus: EventBus | None = None,
    run_id: str = "",
    transport: HttpTransport | None = None,
    environ: dict[str, str] | None = None,
    extra_providers: list[LLMProvider] | None = None,
) -> ProviderRouter | None:
    """Return a router, or None when no AI providers are configured."""
    env = environ if environ is not None else dict(os.environ)
    if extra_providers:
        providers: list[LLMProvider] = list(extra_providers)
    else:
        names = list(settings.ai.candidates) or list(settings.ai.providers)
        if not names:
            return None
        providers = []
        for name in names:
            spec = settings.ai.providers.get(name)
            if spec is None:
                raise AuthoringError(
                    f"ai.candidates lists '{name}' but [profile.*.ai.providers.{name}] is missing."
                )
            st = _status_for(name, spec, env)
            if not st.usable:
                continue
            providers.append(_make_provider(name, spec, env, transport))
        if not providers:
            return None
    return ProviderRouter(
        providers,
        budget_per_call_usd=settings.ai.budget_per_call_usd,
        budget_per_run_usd=settings.ai.budget_per_run_usd,
        store=store,
        bus=bus,
        run_id=run_id,
        pricing=load_pricing(),
        models=dict(settings.ai.models),
    )


def build_named_provider(
    settings: Settings,
    name: str,
    *,
    transport: HttpTransport | None = None,
    environ: dict[str, str] | None = None,
) -> LLMProvider:
    env = environ if environ is not None else dict(os.environ)
    spec = settings.ai.providers.get(name)
    if spec is None:
        raise AuthoringError(f"Unknown AI provider '{name}'.")
    return _make_provider(name, spec, env, transport)


def _status_for(name: str, spec: AiProviderSettings, env: dict[str, str]) -> ProviderStatus:
    kind = spec.kind.strip().lower()
    model = spec.model or ""
    if kind in _KINDS_NEEDING_KEY:
        env_name = spec.api_key_env or ""
        if not env_name:
            return ProviderStatus(
                name, kind, model, False, "api_key_env is missing", None
            )
        if not (env.get(env_name) or "").strip():
            return ProviderStatus(
                name,
                kind,
                model,
                False,
                f"{env_name} unset",
                env_name,
            )
        return ProviderStatus(name, kind, model, True, "key present (value hidden)", env_name)
    if kind == "ollama":
        return ProviderStatus(name, kind, model, True, "local (no key)", None)
    if kind == "cursor_cli":
        return ProviderStatus(
            name, kind, model, True, "experimental (binary checked at call time)", None
        )
    if kind == "fake":
        return ProviderStatus(name, kind, model, True, "fake transport", None)
    return ProviderStatus(name, kind, model, False, f"unknown kind {kind!r}", spec.api_key_env)


def _make_provider(
    name: str,
    spec: AiProviderSettings,
    env: dict[str, str],
    transport: HttpTransport | None,
) -> LLMProvider:
    kind = spec.kind.strip().lower()
    timeout = spec.timeout_s
    if kind == "openai_compat":
        if not spec.base_url or not spec.model or not spec.api_key_env:
            raise AuthoringError(
                f"provider '{name}' needs base_url, model, and api_key_env (env var NAME)."
            )
        return OpenAICompatProvider(
            name=name,
            base_url=spec.base_url,
            model=spec.model,
            api_key_env=spec.api_key_env,
            transport=transport,
            environ=env,
            timeout_s=timeout,
        )
    if kind == "ollama":
        return OllamaProvider(
            name=name,
            base_url=spec.base_url or "http://127.0.0.1:11434",
            model=spec.model or "llama3.2",
            transport=transport,
            timeout_s=timeout,
        )
    if kind == "anthropic":
        if not spec.api_key_env:
            raise AuthoringError(f"provider '{name}' needs api_key_env (env var NAME).")
        return AnthropicProvider(
            name=name,
            base_url=spec.base_url or "https://api.anthropic.com",
            model=spec.model or "claude-sonnet-4-0",
            api_key_env=spec.api_key_env,
            transport=transport,
            environ=env,
            timeout_s=timeout,
        )
    if kind == "cursor_cli":
        from questline.ai.providers.cursor_cli import CursorCliProvider

        return CursorCliProvider(
            name=name,
            model=spec.model or "cursor-cli",
            timeout_s=timeout,
        )
    if kind == "fake":
        return FakeProvider(name=name, model=spec.model or "fake-test")
    raise ProviderError(f"unknown LLM provider kind {kind!r}")
