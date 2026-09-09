"""OpenAI-compatible chat completions (Mistral, Groq, OpenRouter, …)."""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any

from questline.ai.http import HttpTransport, UrllibHttpTransport
from questline.ai.port import ImagePart, LlmRequest, LlmResponse, TokenUsage, ToolCall
from questline.core.errors import ProviderError


class OpenAICompatProvider:
    """POST {base_url}/chat/completions. Key is read from the named env var."""

    kind = "openai_compat"

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        model: str,
        api_key_env: str,
        transport: HttpTransport | None = None,
        environ: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self._transport = transport or UrllibHttpTransport()
        self._environ = environ if environ is not None else dict(os.environ)
        self.timeout_s = timeout_s

    def complete(self, req: LlmRequest) -> LlmResponse:
        key = (self._environ.get(self.api_key_env) or "").strip()
        if not key:
            raise ProviderError(
                f"{self.name}: env {self.api_key_env} is unset. "
                "Set the variable; never put the value in questline.toml."
            )
        model = req.model or self.model
        payload: dict[str, Any] = {
            "model": model,
            "messages": _messages(req),
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        if req.tools:
            payload["tools"] = list(req.tools)
        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        started = time.perf_counter()
        resp = self._transport.request(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            body=body,
            timeout_s=req.timeout_s or self.timeout_s,
        )
        duration_ms = (time.perf_counter() - started) * 1000.0
        data = resp.json()
        choice = _first_choice(data)
        message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
        text = str(message.get("content") or "")
        tool_calls = _parse_tool_calls(message.get("tool_calls"))
        usage = _parse_usage(data.get("usage"))
        return LlmResponse(
            text=text,
            tool_calls=tool_calls,
            usage=usage,
            provider=self.name,
            model=str(data.get("model") or model),
            duration_ms=duration_ms,
        )


def _messages(req: LlmRequest) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if req.system:
        out.append({"role": "system", "content": req.system})
    images = list(req.images or ())
    for i, msg in enumerate(req.messages):
        if i == 0 and images and msg.role == "user":
            out.append({"role": "user", "content": _multimodal(msg.content, images)})
            images = []
        else:
            out.append({"role": msg.role, "content": msg.content})
    if images:
        out.append({"role": "user", "content": _multimodal("", images)})
    return out


def _multimodal(text: str, images: list[ImagePart]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    if text:
        parts.append({"type": "text", "text": text})
    for img in images:
        b64 = base64.b64encode(img.data).decode("ascii")
        url = f"data:{img.media_type};base64,{b64}"
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts


def _first_choice(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError("openai-compat response missing choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ProviderError("openai-compat choice is not an object")
    return first


def _parse_tool_calls(raw: Any) -> tuple[ToolCall, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[ToolCall] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fn = item.get("function") if isinstance(item.get("function"), dict) else {}
        out.append(
            ToolCall(
                id=str(item.get("id") or ""),
                name=str(fn.get("name") or ""),
                arguments=str(fn.get("arguments") or ""),
            )
        )
    return tuple(out)


def _parse_usage(raw: Any) -> TokenUsage:
    if not isinstance(raw, dict):
        return TokenUsage()
    tokens_in = int(raw.get("prompt_tokens") or raw.get("input_tokens") or 0)
    tokens_out = int(raw.get("completion_tokens") or raw.get("output_tokens") or 0)
    details = raw.get("prompt_tokens_details")
    cached_tokens = 0
    if isinstance(details, dict):
        cached_tokens = int(details.get("cached_tokens") or 0)
    return TokenUsage(
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cached=cached_tokens > 0,
        cached_tokens=cached_tokens,
    )
