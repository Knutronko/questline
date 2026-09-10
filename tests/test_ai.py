"""Phase-11 LLMPort: adapters, router, budget, prompts (fake transports)."""

from __future__ import annotations

import json
import subprocess
from email.message import Message
from pathlib import Path

import pytest

from questline.ai.errors import BudgetExceededError, RateLimitedError
from questline.ai.factory import build_router, provider_statuses
from questline.ai.http import FakeHttpTransport
from questline.ai.port import ImagePart, LlmMessage, LlmRequest, TokenUsage
from questline.ai.pricing import load_pricing
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.ai.providers.anthropic import AnthropicProvider
from questline.ai.providers.cursor_cli import CursorCliProvider
from questline.ai.providers.fake import FakeProvider
from questline.ai.providers.ollama import OllamaProvider
from questline.ai.providers.openai_compat import OpenAICompatProvider
from questline.ai.router import ProviderRouter
from questline.core.config import load_settings
from questline.core.errors import AuthoringError, ProviderError
from questline.core.store import RunStore

_REQ = LlmRequest(
    messages=(LlmMessage(role="user", content="ping"),),
    max_tokens=8,
    purpose_tag="test",
)


def _openai_body(text: str = "pong", *, prompt=3, completion=2) -> dict:
    return {
        "model": "mistral-small-latest",
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": prompt, "completion_tokens": completion},
    }


def test_openai_compat_fake_http() -> None:
    http = FakeHttpTransport()
    http.enqueue_json(200, _openai_body())
    provider = OpenAICompatProvider(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        model="mistral-small-latest",
        api_key_env="MISTRAL_API_KEY",
        transport=http,
        environ={"MISTRAL_API_KEY": "not-a-real-key"},
    )
    resp = provider.complete(_REQ)
    assert resp.text == "pong"
    assert resp.usage.tokens_in == 3
    assert resp.usage.tokens_out == 2
    assert http.requests[0]["url"].endswith("/chat/completions")
    assert "Bearer" in http.requests[0]["headers"]["Authorization"]


def test_openai_compat_429() -> None:
    http = FakeHttpTransport()
    http.enqueue_json(429, {"error": "rate"}, headers={"Retry-After": "1"})
    provider = OpenAICompatProvider(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        model="mistral-small-latest",
        api_key_env="MISTRAL_API_KEY",
        transport=http,
        environ={"MISTRAL_API_KEY": "x"},
    )
    with pytest.raises(RateLimitedError):
        provider.complete(_REQ)


def test_ollama_cost_is_zero(tmp_path: Path) -> None:
    http = FakeHttpTransport()
    http.enqueue_json(
        200,
        {
            "model": "llama3.2",
            "message": {"role": "assistant", "content": "hi"},
            "prompt_eval_count": 10,
            "eval_count": 5,
        },
    )
    provider = OllamaProvider(transport=http)
    store = RunStore(tmp_path / "s.db")
    try:
        router = ProviderRouter(
            [provider],
            budget_per_call_usd=1.0,
            budget_per_run_usd=1.0,
            store=store,
            run_id="r1",
        )
        out = router.complete(_REQ)
        assert out.text == "hi"
        rows = store.list_ai_calls(run_id="r1")
        assert len(rows) == 1
        assert rows[0]["cost"] == 0.0
        assert rows[0]["outcome"] == "ok"
    finally:
        store.close()


def test_anthropic_fake_http() -> None:
    http = FakeHttpTransport()
    http.enqueue_json(
        200,
        {
            "model": "claude-sonnet-4-0",
            "content": [{"type": "text", "text": "ok"}],
            "usage": {"input_tokens": 4, "output_tokens": 1},
        },
    )
    provider = AnthropicProvider(
        transport=http,
        environ={"ANTHROPIC_API_KEY": "x"},
    )
    resp = provider.complete(_REQ)
    assert resp.text == "ok"
    assert resp.usage.tokens_in == 4


def test_cursor_cli_fake_runner() -> None:
    def runner(argv, **kwargs):
        assert argv[0] == "cursor-agent"
        return subprocess.CompletedProcess(argv, 0, stdout="cli-pong\n", stderr="")

    provider = CursorCliProvider(runner=runner)
    resp = provider.complete(_REQ)
    assert resp.text == "cli-pong"


def test_cursor_cli_rejects_images() -> None:
    provider = CursorCliProvider(runner=lambda *a, **k: None)
    req = LlmRequest(
        messages=(LlmMessage(role="user", content="see"),),
        images=(ImagePart(media_type="image/png", data=b"x"),),
    )
    with pytest.raises(ProviderError, match="image"):
        provider.complete(req)


def test_router_429_falls_back_both_ledgered(tmp_path: Path) -> None:
    primary = FakeProvider(name="mistral", model="mistral-small-latest")
    primary.enqueue(RateLimitedError("429"))
    secondary = FakeProvider(name="groq", model="llama-3.3-70b-versatile")
    secondary.enqueue("recovered")
    store = RunStore(tmp_path / "s.db")
    try:
        router = ProviderRouter(
            [primary, secondary],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="r1",
        )
        resp = router.complete(_REQ)
        assert resp.text == "recovered"
        rows = store.list_ai_calls(run_id="r1")
        assert len(rows) == 2
        assert rows[0]["provider"] == "mistral"
        assert rows[0]["outcome"] == "rate_limited"
        assert rows[1]["provider"] == "groq"
        assert rows[1]["outcome"] == "ok"
    finally:
        store.close()


def test_router_fallback_keeps_each_provider_model(tmp_path: Path) -> None:
    """Profile models.fast must not stamp the primary vendor id onto Groq/Ollama."""
    primary = FakeProvider(name="mistral", model="mistral-small-latest")
    primary.enqueue(RateLimitedError("429"))
    secondary = FakeProvider(name="groq", model="llama-3.3-70b-versatile")
    secondary.enqueue("recovered")
    store = RunStore(tmp_path / "s.db")
    try:
        router = ProviderRouter(
            [primary, secondary],
            budget_per_call_usd=10.0,
            budget_per_run_usd=10.0,
            store=store,
            run_id="r1",
            models={"fast": "mistral-small-latest", "strong": "mistral-large-latest"},
        )
        resp = router.complete(_REQ)
        assert resp.text == "recovered"
        assert secondary.last_request is not None
        assert secondary.last_request.model == "llama-3.3-70b-versatile"
        rows = store.list_ai_calls(run_id="r1")
        assert rows[0]["model"] == "mistral-small-latest"
        assert rows[1]["model"] == "llama-3.3-70b-versatile"
    finally:
        store.close()


def test_budget_exceeded_in_loop(tmp_path: Path) -> None:
    fake = FakeProvider(usage=TokenUsage(tokens_in=1000, tokens_out=1000))
    store = RunStore(tmp_path / "s.db")
    try:
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=10.0,
            budget_per_run_usd=3.0,
            store=store,
            run_id="loop",
        )
        router.complete(_REQ)
        with pytest.raises(BudgetExceededError) as exc:
            router.complete(_REQ)
        assert exc.value.kind in {"run", "call"}
        rows = store.list_ai_calls(run_id="loop")
        assert len(rows) == 2
        assert all(r["outcome"] == "ok" for r in rows)
    finally:
        store.close()


def test_per_call_budget_hard_stop(tmp_path: Path) -> None:
    fake = FakeProvider(usage=TokenUsage(tokens_in=1000, tokens_out=1000))
    store = RunStore(tmp_path / "s.db")
    try:
        router = ProviderRouter(
            [fake],
            budget_per_call_usd=0.01,
            budget_per_run_usd=100.0,
            store=store,
            run_id="c",
        )
        with pytest.raises(BudgetExceededError) as exc:
            router.complete(_REQ)
        assert exc.value.kind == "call"
        assert store.list_ai_calls(run_id="c")
    finally:
        store.close()


def test_prompt_store_and_stable_prefix() -> None:
    text = load_prompt("lens_implications", "v1")
    assert "model reasoning" in text
    assert "Never invent" in text or "never invent" in text.lower()
    composed = compose_stable_prefix("SYSTEM", "USER JSON")
    assert composed.startswith("SYSTEM")
    with pytest.raises(AuthoringError):
        load_prompt("nope", "v9")


def test_urllib_transport_429(monkeypatch: pytest.MonkeyPatch) -> None:
    import io
    import urllib.error

    from questline.ai.http import UrllibHttpTransport

    hdrs = Message()
    hdrs["Retry-After"] = "2"

    def boom(req, timeout=None):
        raise urllib.error.HTTPError(
            url="https://example.invalid/v1",
            code=429,
            msg="rate",
            hdrs=hdrs,
            fp=io.BytesIO(b'{"error":"rate"}'),
        )

    monkeypatch.setattr("questline.ai.http.urllib.request.urlopen", boom)
    with pytest.raises(RateLimitedError) as exc:
        UrllibHttpTransport().request(
            "POST",
            "https://example.invalid/v1",
            headers={},
            body=b"{}",
            timeout_s=1.0,
        )
    assert exc.value.retry_after_s == 2.0


def test_urllib_transport_sets_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    from questline.ai.http import UrllibHttpTransport

    captured: dict[str, str] = {}

    class _FakeResp:
        status = 200
        headers = {}

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self) -> _FakeResp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(req, timeout=None):
        captured.update({k.lower(): v for k, v in req.header_items()})
        return _FakeResp()

    monkeypatch.setattr("questline.ai.http.urllib.request.urlopen", fake_urlopen)
    UrllibHttpTransport().request(
        "POST",
        "https://example.invalid/v1",
        headers={"Authorization": "Bearer x", "Content-Type": "application/json"},
        body=b"{}",
        timeout_s=1.0,
    )
    assert captured.get("user-agent") == "questline"
    assert captured.get("authorization") == "Bearer x"


def test_pricing_unknown_model_uses_fallback() -> None:
    table = load_pricing()
    cost = table.estimate(model="mystery", kind="openai_compat", tokens_in=1_000_000, tokens_out=0)
    assert cost == pytest.approx(1.0)


def test_config_api_key_env_allowed_nested_secret_rejected(tmp_path: Path) -> None:
    good = tmp_path / "ok.toml"
    good.write_text(
        """
[profile.ai_mistral]
ai.candidates = ["mistral"]
[profile.ai_mistral.ai.providers.mistral]
kind = "openai_compat"
base_url = "https://api.mistral.ai/v1"
model = "mistral-small-latest"
api_key_env = "MISTRAL_API_KEY"
""",
        encoding="utf-8",
    )
    settings = load_settings(
        config_path=good, profile="ai_mistral", project_root=tmp_path, environ={}
    )
    assert settings.ai.providers["mistral"].api_key_env == "MISTRAL_API_KEY"
    statuses = provider_statuses(settings, environ={})
    assert statuses[0].usable is False
    assert "unset" in statuses[0].detail

    bad = tmp_path / "bad.toml"
    bad.write_text(
        """
[profile.x]
[profile.x.ai.providers.mistral]
kind = "openai_compat"
api_key = "leaked"
""",
        encoding="utf-8",
    )
    with pytest.raises(AuthoringError, match="Secret field"):
        load_settings(config_path=bad, profile="x", project_root=tmp_path, environ={})


def test_build_router_missing_provider_spec(tmp_path: Path) -> None:
    cfg = tmp_path / "q.toml"
    cfg.write_text(
        """
[profile.p]
ai.candidates = ["ghost"]
""",
        encoding="utf-8",
    )
    settings = load_settings(config_path=cfg, profile="p", project_root=tmp_path, environ={})
    with pytest.raises(AuthoringError, match="ghost"):
        build_router(settings, environ={})


def test_openai_compat_missing_key() -> None:
    provider = OpenAICompatProvider(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        model="mistral-small-latest",
        api_key_env="MISTRAL_API_KEY",
        transport=FakeHttpTransport(),
        environ={},
    )
    with pytest.raises(ProviderError, match="unset"):
        provider.complete(_REQ)


def test_openai_compat_images_and_tools() -> None:
    http = FakeHttpTransport()
    http.enqueue_json(
        200,
        {
            "model": "mistral-small-latest",
            "choices": [
                {
                    "message": {
                        "content": "saw",
                        "tool_calls": [
                            {
                                "id": "1",
                                "function": {"name": "x", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 2,
                "completion_tokens": 1,
                "prompt_tokens_details": {"cached_tokens": 1},
            },
        },
    )
    provider = OpenAICompatProvider(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
        model="mistral-small-latest",
        api_key_env="MISTRAL_API_KEY",
        transport=http,
        environ={"MISTRAL_API_KEY": "x"},
    )
    req = LlmRequest(
        system="sys",
        messages=(LlmMessage(role="user", content="look"),),
        images=(ImagePart(media_type="image/png", data=b"\x89PNG"),),
        tools=({"type": "function", "function": {"name": "x"}},),
        purpose_tag="test",
    )
    resp = provider.complete(req)
    assert resp.text == "saw"
    assert resp.tool_calls[0].name == "x"
    assert resp.usage.cached is True
    body = json.loads(http.requests[0]["body"].decode())
    assert body["messages"][0]["role"] == "system"


def test_build_router_skips_unset_keys_uses_fallback(tmp_path: Path) -> None:
    cfg = tmp_path / "q.toml"
    cfg.write_text(
        """
[profile.p]
ai.candidates = ["mistral", "fake"]
ai.budget_per_call_usd = 10
ai.budget_per_run_usd = 10
[profile.p.ai.providers.mistral]
kind = "openai_compat"
base_url = "https://example.invalid/v1"
model = "mistral-small-latest"
api_key_env = "MISTRAL_API_KEY"
[profile.p.ai.providers.fake]
kind = "fake"
model = "fake-test"
""",
        encoding="utf-8",
    )
    settings = load_settings(config_path=cfg, profile="p", project_root=tmp_path, environ={})
    store = RunStore(tmp_path / "s.db")
    try:
        router = build_router(settings, store=store, run_id="r", environ={})
        assert router is not None
        resp = router.complete(_REQ)
        assert resp.provider == "fake"
    finally:
        store.close()


def test_doctor_ping_pins_provider_model_not_profile_fast(tmp_path: Path) -> None:
    from questline.ai.doctor import ping_providers

    cfg = tmp_path / "q.toml"
    cfg.write_text(
        """
[profile.p]
driver = "mock"
ai.candidates = ["fake"]
ai.models.fast = "mistral-small-latest"
ai.budget_per_call_usd = 10
ai.budget_per_run_usd = 10
[profile.p.ai.providers.fake]
kind = "fake"
model = "fake-test"
""",
        encoding="utf-8",
    )
    settings = load_settings(config_path=cfg, profile="p", project_root=tmp_path, environ={})
    results = ping_providers(settings)
    assert results[0].usable
    assert "fake-test" in results[0].detail
