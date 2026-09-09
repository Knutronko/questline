"""Thin Anthropic Messages API adapter."""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any

from questline.ai.http import HttpTransport, UrllibHttpTransport
from questline.ai.port import ImagePart, LlmRequest, LlmResponse, TokenUsage, ToolCall
from questline.core.errors import ProviderError


class AnthropicProvider:
    """POST {base_url}/v1/messages. Key from the named env var."""

    kind = "anthropic"

    def __init__(
        self,
        *,
        name: str = "anthropic",
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-sonnet-4-0",
        api_key_env: str = "ANTHROPIC_API_KEY",
        transport: HttpTransport | None = None,
        environ: dict[str, str] | None = None,
        timeout_s: float = 30.0,
        api_version: str = "2023-06-01",
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self._transport = transport or UrllibHttpTransport()
        self._environ = environ if environ is not None else dict(os.environ)
        self.timeout_s = timeout_s
        self.api_version = api_version

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
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": _messages(req),
        }
        if req.system:
            payload["system"] = req.system
        if req.tools:
            payload["tools"] = list(req.tools)
        started = time.perf_counter()
        resp = self._transport.request(
            "POST",
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": self.api_version,
                "content-type": "application/json",
            },
            body=json.dumps(payload).encode("utf-8"),
            timeout_s=req.timeout_s or self.timeout_s,
        )
        duration_ms = (time.perf_counter() - started) * 1000.0
        data = resp.json()
        text, tool_calls = _parse_content(data.get("content"))
        usage_raw = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        tokens_in = int(usage_raw.get("input_tokens") or 0)
        tokens_out = int(usage_raw.get("output_tokens") or 0)
        cache_read = int(usage_raw.get("cache_read_input_tokens") or 0)
        return LlmResponse(
            text=text,
            tool_calls=tool_calls,
            usage=TokenUsage(
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cached=cache_read > 0,
                cached_tokens=cache_read,
            ),
            provider=self.name,
            model=str(data.get("model") or model),
            duration_ms=duration_ms,
        )


def _messages(req: LlmRequest) -> list[dict[str, Any]]:
    images = list(req.images or ())
    out: list[dict[str, Any]] = []
    for i, msg in enumerate(req.messages):
        if msg.role == "system":
            continue
        if i == 0 and images and msg.role == "user":
            out.append({"role": "user", "content": _blocks(msg.content, images)})
            images = []
        else:
            out.append({"role": msg.role, "content": msg.content})
    if images:
        out.append({"role": "user", "content": _blocks("", images)})
    return out


def _blocks(text: str, images: list[ImagePart]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    if text:
        parts.append({"type": "text", "text": text})
    for img in images:
        parts.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.media_type,
                    "data": base64.b64encode(img.data).decode("ascii"),
                },
            }
        )
    return parts


def _parse_content(raw: Any) -> tuple[str, tuple[ToolCall, ...]]:
    if not isinstance(raw, list):
        return (str(raw or ""), ())
    texts: list[str] = []
    tools: list[ToolCall] = []
    for block in raw:
        if not isinstance(block, dict):
            continue
        kind = str(block.get("type") or "")
        if kind == "text":
            texts.append(str(block.get("text") or ""))
        elif kind == "tool_use":
            tools.append(
                ToolCall(
                    id=str(block.get("id") or ""),
                    name=str(block.get("name") or ""),
                    arguments=json.dumps(block.get("input") or {}),
                )
            )
    return ("".join(texts), tuple(tools))
