"""LLMPort protocol and request/response types (architecture §3.5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ImagePart:
    """Native image block. Agents must not pass a base64 string as 'text'."""

    media_type: str
    data: bytes


@dataclass(frozen=True, slots=True)
class LlmMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class TokenUsage:
    tokens_in: int = 0
    tokens_out: int = 0
    cached: bool = False
    cached_tokens: int = 0


@dataclass(frozen=True, slots=True)
class LlmRequest:
    messages: tuple[LlmMessage, ...]
    system: str | None = None
    tools: tuple[dict[str, Any], ...] | None = None
    images: tuple[ImagePart, ...] | None = None
    max_tokens: int = 256
    temperature: float = 0.0
    purpose_tag: str = ""
    model_class: str = "fast"
    model: str | None = None
    timeout_s: float = 30.0


@dataclass(frozen=True, slots=True)
class LlmResponse:
    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: TokenUsage = field(default_factory=TokenUsage)
    provider: str = ""
    model: str = ""
    duration_ms: float = 0.0


@runtime_checkable
class LLMProvider(Protocol):
    """One configured backend. Router owns fallback and budget."""

    name: str
    model: str
    kind: str

    def complete(self, req: LlmRequest) -> LlmResponse: ...
