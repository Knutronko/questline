"""Local Ollama chat API — always zero cost."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

from questline.ai.http import HttpTransport, UrllibHttpTransport
from questline.ai.port import LlmRequest, LlmResponse, TokenUsage


class OllamaProvider:
    """POST {base_url}/api/chat (stream=false). No API key."""

    kind = "ollama"

    def __init__(
        self,
        *,
        name: str = "ollama",
        base_url: str = "http://127.0.0.1:11434",
        model: str = "llama3.2",
        transport: HttpTransport | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self.name = name
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._transport = transport or UrllibHttpTransport()
        self.timeout_s = timeout_s

    def complete(self, req: LlmRequest) -> LlmResponse:
        model = req.model or self.model
        messages: list[dict[str, Any]] = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        images_b64 = [
            base64.b64encode(img.data).decode("ascii") for img in (req.images or ())
        ]
        for i, msg in enumerate(req.messages):
            row: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if i == 0 and images_b64:
                row["images"] = images_b64
                images_b64 = []
            messages.append(row)
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": req.max_tokens, "temperature": req.temperature},
        }
        started = time.perf_counter()
        resp = self._transport.request(
            "POST",
            f"{self.base_url}/api/chat",
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8"),
            timeout_s=req.timeout_s or self.timeout_s,
        )
        duration_ms = (time.perf_counter() - started) * 1000.0
        data = resp.json()
        message = data.get("message") if isinstance(data.get("message"), dict) else {}
        text = str(message.get("content") or data.get("response") or "")
        prompt_eval = int(data.get("prompt_eval_count") or 0)
        eval_count = int(data.get("eval_count") or 0)
        return LlmResponse(
            text=text,
            usage=TokenUsage(tokens_in=prompt_eval, tokens_out=eval_count),
            provider=self.name,
            model=str(data.get("model") or model),
            duration_ms=duration_ms,
        )
