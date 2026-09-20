"""In-memory LLM provider for CI. No network."""

from __future__ import annotations

from dataclasses import dataclass, field

from questline.ai.port import LlmRequest, LlmResponse, TokenUsage, ToolCall

_QueueItem = str | BaseException | LlmResponse


@dataclass
class FakeProvider:
    """Scripted completions. Queue an exception to simulate 429 / 5xx."""

    name: str = "fake"
    model: str = "fake-test"
    kind: str = "fake"
    queue: list[_QueueItem] = field(default_factory=list)
    usage: TokenUsage = field(default_factory=lambda: TokenUsage(tokens_in=1000, tokens_out=1000))
    last_request: LlmRequest | None = None
    requests: list[LlmRequest] = field(default_factory=list)

    def enqueue(self, item: _QueueItem) -> None:
        self.queue.append(item)

    def enqueue_tools(self, *calls: ToolCall, text: str = "") -> None:
        """Queue a tool-call turn (FP-G4 fake loop)."""
        self.queue.append(
            LlmResponse(
                text=text,
                tool_calls=calls,
                usage=self.usage,
                provider=self.name,
                model=self.model,
                duration_ms=1.0,
            )
        )

    def complete(self, req: LlmRequest) -> LlmResponse:
        self.last_request = req
        self.requests.append(req)
        if self.queue:
            item = self.queue.pop(0)
            if isinstance(item, BaseException):
                raise item
            if isinstance(item, LlmResponse):
                return item
            text = item
        else:
            text = "fake-ok"
        return LlmResponse(
            text=text,
            usage=self.usage,
            provider=self.name,
            model=req.model or self.model,
            duration_ms=1.0,
        )
