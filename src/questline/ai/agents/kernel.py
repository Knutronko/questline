"""Shared tool-use loop over LLMPort (phase-12 test agents).

GameLens Ask stays in questline.lens.agent — this kernel is not that loop.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from questline.ai.agents.persist import persist_task
from questline.ai.agents.schema import parse_agent_output
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import (
    ToolContext,
    ToolSpec,
    looks_like_write_command,
    parse_args,
    schemas_for,
)
from questline.ai.port import ImagePart, LlmMessage, LlmRequest
from questline.core.store import RunStore

DEFAULT_MAX_TURNS = 8
MAX_TOOL_RESULT_CHARS = 8000


class AgentKernel:
    """Allow-listed tools, per-task turn budget, incremental persist, hermetic RO."""

    def __init__(
        self,
        store: RunStore,
        *,
        router: Any | None,
        ctx: ToolContext,
        max_turns: int = DEFAULT_MAX_TURNS,
        read_only: bool = True,
        purpose_tag: str = "agent.kernel",
        max_tokens: int = 512,
        must_write: bool = False,
    ) -> None:
        self.store = store
        self.router = router
        self.ctx = ctx
        self.max_turns = max(1, int(max_turns))
        self.read_only = read_only
        self.purpose_tag = purpose_tag
        self.max_tokens = max(64, int(max_tokens))
        self.must_write = must_write

    def run_batch(
        self,
        jobs: Sequence[tuple[AgentTask, str, str, Sequence[ToolSpec]]],
    ) -> list[AgentTask]:
        """Each job gets a fresh turn budget — a greedy task cannot starve the rest."""
        out: list[AgentTask] = []
        for task, system, user, tools in jobs:
            out.append(self.run(task, system=system, user=user, tools=tools))
        return out

    def run(
        self,
        task: AgentTask,
        *,
        system: str,
        user: str,
        tools: Sequence[ToolSpec],
    ) -> AgentTask:
        if not task.created_at:
            task.created_at = datetime.now().astimezone().isoformat()
        if not task.purpose_tag:
            task.purpose_tag = self.purpose_tag
        task.status = "running"
        persist_task(self.store, task)

        specs = list(tools)
        allowed = {s.name: s for s in specs if not (self.read_only and s.write)}
        schemas = schemas_for(specs, read_only=self.read_only)

        if self.router is None:
            task.status = "skipped"
            task.pending = "no-provider"
            task.verdict = "inconclusive"
            task.cause = "unknown"
            task.summary = task.summary or "No LLM provider configured (see docs/ai-setup.md)."
            persist_task(self.store, task)
            return task

        messages: list[LlmMessage] = [LlmMessage(role="user", content=user)]
        pending_images: tuple[ImagePart, ...] | None = None
        finished = False
        write_nudges = 0

        for step in range(self.max_turns):
            try:
                resp = self.router.complete(
                    LlmRequest(
                        system=system,
                        messages=tuple(messages),
                        tools=schemas or None,
                        images=pending_images,
                        max_tokens=self.max_tokens,
                        temperature=0.0,
                        purpose_tag=task.purpose_tag or self.purpose_tag,
                        model_class="fast",
                    )
                )
            except Exception as exc:
                task.status = "error"
                task.pending = type(exc).__name__
                task.verdict = task.verdict or "inconclusive"
                task.cause = task.cause or "unknown"
                task.summary = f"LLMPort failed ({type(exc).__name__}: {exc})"
                persist_task(self.store, task)
                return task
            pending_images = None
            self.ctx.pending_images.clear()

            if resp.text:
                task.evidence.append(
                    {"kind": "model_text", "text": str(resp.text)[:6000]}
                )

            if resp.tool_calls:
                results: list[dict[str, Any]] = []
                for call in resp.tool_calls:
                    result = self._dispatch(allowed, call.name, call.arguments)
                    entry = {
                        "turn": step + 1,
                        "name": call.name,
                        "arguments": parse_args(call.arguments),
                        "ok": "error" not in result,
                    }
                    task.tool_log.append(entry)
                    results.append(result)
                    persist_task(self.store, task, log_line=entry)
                if self.ctx.pending_images:
                    pending_images = tuple(self.ctx.pending_images)
                messages.append(
                    LlmMessage(
                        role="user",
                        content="TOOL RESULTS:\n"
                        + _clip(json.dumps(results, sort_keys=True, default=str)),
                    )
                )
                continue

            wrote = any(
                e.get("name") == "write_file" and e.get("ok") for e in task.tool_log
            )
            if self.must_write and not wrote and write_nudges < 2:
                write_nudges += 1
                messages.append(
                    LlmMessage(
                        role="user",
                        content=(
                            "REQUIRED: call write_file now. path must be WRITE_TEST_TO. "
                            "content is the full pytest source. Do not finish with JSON "
                            "until write_file returns ok."
                        ),
                    )
                )
                continue

            parsed = parse_agent_output(resp.text or "")
            task.agent_claim = parsed
            task.summary = str(parsed.get("summary") or resp.text or "")
            task.verdict = str(parsed.get("verdict") or "inconclusive")
            task.cause = str(parsed.get("cause") or "unknown")
            if parsed.get("evidence"):
                kept = [
                    e
                    for e in task.evidence
                    if isinstance(e, dict) and e.get("kind") == "model_text"
                ]
                task.evidence = kept + list(parsed["evidence"])
            if parsed.get("clusters"):
                task.clusters = list(parsed["clusters"])
            if parsed.get("suggestion"):
                task.suggestion = parsed["suggestion"]
            task.status = "ok"
            task.pending = None
            finished = True
            persist_task(self.store, task)
            break

        if not finished and task.status == "running":
            task.status = "truncated"
            task.pending = "max-turns"
            task.verdict = task.verdict or "inconclusive"
            task.cause = task.cause or "unknown"
            task.summary = task.summary or "Turn budget reached before a final reply."
            persist_task(self.store, task)
        return task

    def _dispatch(
        self, allowed: dict[str, ToolSpec], name: str, raw_args: str
    ) -> dict[str, Any]:
        args = parse_args(raw_args)
        spec = allowed.get(name)
        if spec is None:
            return {
                "tool": name,
                "error": (
                    f"tool {name!r} not allow-listed"
                    + (" (read-only mode)" if self.read_only else "")
                ),
            }
        if spec.shell:
            command = str(args.get("command") or "")
            if looks_like_write_command(command):
                return {
                    "tool": name,
                    "error": "write pattern blocked (hermetic read-only)",
                }
        try:
            return spec.handler(self.ctx, args)
        except Exception as exc:
            return {"tool": name, "error": f"{type(exc).__name__}: {exc}"}


def new_task_id(prefix: str = "ag") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _clip(text: str) -> str:
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    return text[: MAX_TOOL_RESULT_CHARS - 20] + "\n…[truncated]"
