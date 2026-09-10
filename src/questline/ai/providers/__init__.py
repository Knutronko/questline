"""LLM provider adapters. Cursor CLI is experimental and must stay isolated."""

from __future__ import annotations

from questline.ai.providers.anthropic import AnthropicProvider
from questline.ai.providers.fake import FakeProvider
from questline.ai.providers.ollama import OllamaProvider
from questline.ai.providers.openai_compat import OpenAICompatProvider

# Do not import CursorCliProvider here — import-linter forbids core/agents; this
# package init is imported by factory/router tests. Load cursor_cli lazily.

__all__ = [
    "AnthropicProvider",
    "FakeProvider",
    "OllamaProvider",
    "OpenAICompatProvider",
]
