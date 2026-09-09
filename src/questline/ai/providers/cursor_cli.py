"""Experimental Cursor CLI adapter. Nothing in core/agents may import this module."""

from __future__ import annotations

import shutil
import subprocess
import time
from collections.abc import Callable, Sequence

from questline.ai.port import LlmRequest, LlmResponse, TokenUsage
from questline.core.errors import ProviderError

# Documented limitations (docs/ai-setup.md): print-mode only, no native tool loop,
# image support is not guaranteed, argv surface churns with Cursor CLI releases.

RunFn = Callable[..., subprocess.CompletedProcess[str]]


class CursorCliProvider:
    """Subprocess to ``cursor-agent`` (print mode). Experimental — isolated by import-linter."""

    kind = "cursor_cli"

    def __init__(
        self,
        *,
        name: str = "cursor_cli",
        model: str = "cursor-cli",
        binary: str = "cursor-agent",
        extra_args: Sequence[str] | None = None,
        runner: RunFn | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self.name = name
        self.model = model
        self.binary = binary
        self.extra_args = list(extra_args or ("--print", "--output-format", "text"))
        self._runner = runner or subprocess.run
        self.timeout_s = timeout_s

    def complete(self, req: LlmRequest) -> LlmResponse:
        if req.images:
            raise ProviderError("CursorCliProvider does not accept image blocks")
        prompt = _flatten(req)
        argv = [self.binary, *self.extra_args, prompt]
        if self._runner is subprocess.run and shutil.which(self.binary) is None:
            raise ProviderError(
                f"{self.binary} not on PATH. CursorCliProvider is experimental; "
                "see docs/ai-setup.md."
            )
        started = time.perf_counter()
        try:
            completed = self._runner(
                argv,
                capture_output=True,
                text=True,
                timeout=req.timeout_s or self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"{self.binary} timed out") from exc
        duration_ms = (time.perf_counter() - started) * 1000.0
        if completed.returncode != 0:
            err = (completed.stderr or completed.stdout or "").strip()[:300]
            raise ProviderError(f"{self.binary} exit {completed.returncode}: {err}")
        text = (completed.stdout or "").strip()
        return LlmResponse(
            text=text,
            usage=TokenUsage(),
            provider=self.name,
            model=req.model or self.model,
            duration_ms=duration_ms,
        )


def _flatten(req: LlmRequest) -> str:
    parts: list[str] = []
    if req.system:
        parts.append(req.system)
    for msg in req.messages:
        parts.append(f"{msg.role}: {msg.content}")
    return "\n\n".join(parts)
