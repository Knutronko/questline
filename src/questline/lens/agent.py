"""Thin GameLens balance agent — read-only tool loop over LLMPort (FP-G4)."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from questline.ai.port import LlmMessage, LlmRequest, ToolCall
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.core.store import RunStore
from questline.lens.browse import (
    SnapshotNotFoundError,
    diff_from_store,
    implications_for_pair,
    list_sessions_public,
    list_snapshots_public,
)
from questline.lens.report import collect_measured

PROMPT_NAME = "lens_balance_agent"
PROMPT_VERSION = "v1"
PURPOSE_TAG = "lens.balance_agent"
FRAMING = "model reasoning"
DEFAULT_QUESTION = (
    "What should a human look at for a retune? Priorities only; do not write SOs."
)
MAX_TOOL_RESULT_CHARS = 8000
DEFAULT_MAX_TURNS = 5

TOOL_SCHEMAS: tuple[dict[str, Any], ...] = (
    {
        "type": "function",
        "function": {
            "name": "list_snapshots",
            "description": "List stored balance snapshot ids and versions (config truth).",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diff_snapshots",
            "description": "Typed config diff between two snapshots. Not a verdict.",
            "parameters": {
                "type": "object",
                "properties": {
                    "snapshot_a": {"type": "string"},
                    "snapshot_b": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_implications",
            "description": "Persisted batch *model reasoning* implications for a snapshot pair.",
            "parameters": {
                "type": "object",
                "properties": {
                    "snapshot_a": {"type": "string"},
                    "snapshot_b": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_session_summaries",
            "description": (
                "telemetry_sessions.summary rows (measured). "
                "outcome=lose is measured play. snap-unset cannot join."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "config_snapshot_id": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "collect_measured",
            "description": (
                "Join telemetry_sessions.summary to snapshot A/B. "
                "Returns measured facts and gaps (never imputed)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "snapshot_a": {"type": "string"},
                    "snapshot_b": {"type": "string"},
                },
                "additionalProperties": False,
            },
        },
    },
)

_ALLOWED_TOOLS = frozenset(t["function"]["name"] for t in TOOL_SCHEMAS)


@dataclass
class AgentTurn:
    """One persisted balance-agent conversation (priorities, not SO writes)."""

    id: str
    question: str
    snapshot_id_a: str | None
    snapshot_id_b: str | None
    status: str
    framing: str = FRAMING
    prompt_version: str = PROMPT_VERSION
    purpose_tag: str = PURPOSE_TAG
    summary: str = ""
    pending: str | None = None
    priorities: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    citations: dict[str, Any] = field(default_factory=dict)
    tool_log: list[dict[str, Any]] = field(default_factory=list)
    artifact_path: str | None = None
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "snapshot_id_a": self.snapshot_id_a,
            "snapshot_id_b": self.snapshot_id_b,
            "status": self.status,
            "framing": self.framing,
            "prompt_version": self.prompt_version,
            "purpose_tag": self.purpose_tag,
            "summary": self.summary,
            "pending": self.pending,
            "priorities": list(self.priorities),
            "gaps": list(self.gaps),
            "citations": self.citations,
            "tool_log": list(self.tool_log),
            "artifact_path": self.artifact_path,
            "created_at": self.created_at,
        }


def run_balance_agent(
    store: RunStore,
    *,
    snapshot_a: str,
    snapshot_b: str,
    question: str | None = None,
    router: Any | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    turn_id: str | None = None,
) -> AgentTurn:
    """Read-only tool loop. Persist incrementally. Never writes SOs or imputes KPIs."""
    q = (question or "").strip() or DEFAULT_QUESTION
    tid = turn_id or f"ba-{uuid.uuid4().hex[:16]}"
    created = datetime.now().astimezone().isoformat()
    turn = AgentTurn(
        id=tid,
        question=q,
        snapshot_id_a=snapshot_a,
        snapshot_id_b=snapshot_b,
        status="running",
        created_at=created,
    )
    measured, gaps = _safe_measured(store, snapshot_a, snapshot_b)
    turn.gaps = gaps
    turn.citations = {
        "measured": measured,
        "diff_entry_count": measured.get("diff_entry_count"),
    }
    _persist_turn(store, turn)

    if router is None:
        turn.status = "skipped"
        turn.pending = "no-provider"
        turn.summary = (
            "No LLM provider configured (see docs/ai-setup.md). "
            "Gaps and measured citations are from the store; missing KPIs are not imputed."
        )
        turn.priorities = ()
        _persist_turn(store, turn)
        return turn

    system = load_prompt(PROMPT_NAME, PROMPT_VERSION)
    user = compose_stable_prefix(
        f"SNAPSHOT PAIR: {snapshot_a} -> {snapshot_b}",
        f"OPERATOR QUESTION: {q}",
        "Call tools for measured facts and the typed diff. "
        "Then reply with English priority bullets. Do not invent numbers.",
    )
    messages: list[LlmMessage] = [LlmMessage(role="user", content=user)]
    finished = False
    last_error: str | None = None

    for _step in range(max(1, int(max_turns))):
        try:
            resp = router.complete(
                LlmRequest(
                    system=system,
                    messages=tuple(messages),
                    tools=TOOL_SCHEMAS,
                    max_tokens=512,
                    temperature=0.0,
                    purpose_tag=PURPOSE_TAG,
                    model_class="fast",
                )
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            turn.status = "error"
            turn.summary = (
                f"LLMPort failed ({last_error}). Measured facts unchanged; gaps not imputed."
            )
            _persist_turn(store, turn)
            return turn

        if resp.tool_calls:
            results: list[dict[str, Any]] = []
            for call in resp.tool_calls:
                result = _dispatch_tool(store, snapshot_a, snapshot_b, call)
                turn.tool_log.append(
                    {
                        "name": call.name,
                        "arguments": _parse_args(call.arguments),
                        "ok": "error" not in result,
                    }
                )
                results.append(result)
                _persist_turn(store, turn)
            messages.append(
                LlmMessage(
                    role="user",
                    content="TOOL RESULTS (measured / config truth; do not invent):\n"
                    + _clip(json.dumps(results, sort_keys=True, default=str)),
                )
            )
            continue

        text = (resp.text or "").strip()
        priorities, extra_gaps = _parse_reply(text)
        # Store owns gaps and measured citations — never take numbers from the model.
        measured, gaps = _safe_measured(store, snapshot_a, snapshot_b)
        merged_gaps = _merge_gaps(gaps, extra_gaps)
        turn.summary = text
        turn.priorities = priorities
        turn.gaps = merged_gaps
        turn.citations = {
            "measured": measured,
            "diff_entry_count": _diff_entry_count(store, snapshot_a, snapshot_b),
        }
        turn.status = "ok"
        turn.pending = None
        finished = True
        _persist_turn(store, turn)
        break

    if not finished and turn.status == "running":
        turn.status = "truncated"
        turn.pending = "max-turns"
        turn.summary = (
            turn.summary
            or "Turn budget reached before a final reply. Gaps below are from the store."
        )
        measured, gaps = _safe_measured(store, snapshot_a, snapshot_b)
        turn.gaps = gaps
        turn.citations = {
            "measured": measured,
            "diff_entry_count": _diff_entry_count(store, snapshot_a, snapshot_b),
        }
        _persist_turn(store, turn)
    return turn


def load_turn_artifact(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    target = Path(path)
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _dispatch_tool(
    store: RunStore,
    default_a: str,
    default_b: str,
    call: ToolCall,
) -> dict[str, Any]:
    name = (call.name or "").strip()
    args = _parse_args(call.arguments)
    if name not in _ALLOWED_TOOLS:
        return {
            "tool": name,
            "error": f"unknown tool {name!r}; allow-list is {sorted(_ALLOWED_TOOLS)}",
        }
    try:
        if name == "list_snapshots":
            return {"tool": name, "snapshots": list_snapshots_public(store)}
        if name == "diff_snapshots":
            a = str(args.get("snapshot_a") or default_a)
            b = str(args.get("snapshot_b") or default_b)
            report = diff_from_store(store, a, b)
            payload = report.to_dict()
            payload["tool"] = name
            return payload
        if name == "get_implications":
            a = str(args.get("snapshot_a") or default_a)
            b = str(args.get("snapshot_b") or default_b)
            impl = implications_for_pair(store, a, b)
            return {"tool": name, "implications": impl}
        if name == "list_session_summaries":
            sid = args.get("config_snapshot_id")
            limit = int(args.get("limit") or 50)
            key = str(sid) if sid else None
            return {
                "tool": name,
                "sessions": list_sessions_public(
                    store, config_snapshot_id=key, limit=max(1, min(limit, 100))
                ),
            }
        if name == "collect_measured":
            a = str(args.get("snapshot_a") or default_a)
            b = str(args.get("snapshot_b") or default_b)
            report = diff_from_store(store, a, b)
            measured, gaps = collect_measured(store, report)
            return {
                "tool": name,
                "measured": measured,
                "gaps": list(gaps),
                "diff_entry_count": len(report.entries),
            }
    except SnapshotNotFoundError as exc:
        return {"tool": name, "error": f"unknown snapshot: {exc}"}
    except Exception as exc:
        return {"tool": name, "error": f"{type(exc).__name__}: {exc}"}
    return {"tool": name, "error": "unhandled"}


def _safe_measured(
    store: RunStore, key_a: str, key_b: str
) -> tuple[dict[str, Any], tuple[str, ...]]:
    try:
        report = diff_from_store(store, key_a, key_b)
    except (SnapshotNotFoundError, Exception):
        return {}, ("unknown snapshot pair — cannot join telemetry",)
    measured, gaps = collect_measured(store, report)
    measured = dict(measured)
    measured["diff_entry_count"] = len(report.entries)
    return measured, gaps


def _diff_entry_count(store: RunStore, key_a: str, key_b: str) -> int | None:
    try:
        return len(diff_from_store(store, key_a, key_b).entries)
    except (SnapshotNotFoundError, Exception):
        return None


def _persist_turn(store: RunStore, turn: AgentTurn) -> None:
    dest_dir = store.artifacts_dir / "lens" / "agent" / turn.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / "turn.json"
    turn.artifact_path = str(path)
    payload = turn.to_dict()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    measured = turn.citations.get("measured") if isinstance(turn.citations, dict) else {}
    store.save_lens_agent_turn(
        turn_id=turn.id,
        snapshot_id_a=turn.snapshot_id_a,
        snapshot_id_b=turn.snapshot_id_b,
        question=turn.question,
        status=turn.status,
        framing=turn.framing,
        prompt_version=turn.prompt_version,
        artifact_path=str(path),
        created_at=turn.created_at,
        meta={
            "pending": turn.pending,
            "gap_count": len(turn.gaps),
            "tool_count": len(turn.tool_log),
            "purpose_tag": turn.purpose_tag,
            "session_count": (measured or {}).get("session_count"),
            "unjoined_count": (measured or {}).get("unjoined_count"),
        },
    )


def _parse_args(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _parse_reply(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    blob = _extract_json(text)
    priorities: list[str] = []
    extra_gaps: list[str] = []
    if isinstance(blob, dict):
        raw_p = blob.get("priorities")
        if isinstance(raw_p, list):
            priorities = [str(x).strip() for x in raw_p if str(x).strip()]
        raw_g = blob.get("gaps")
        if isinstance(raw_g, list):
            extra_gaps = [str(x).strip() for x in raw_g if str(x).strip()]
    if not priorities:
        priorities = _bullets(text)
    return tuple(priorities), tuple(extra_gaps)


def _extract_json(text: str) -> dict[str, Any] | None:
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else None
    if candidate is None:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            candidate = stripped
    if candidate is None:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = match.group(0) if match else None
    if not candidate:
        return None
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _bullets(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ", "• ")):
            out.append(stripped[2:].strip())
        else:
            numbered = re.match(r"^\d+[\.)]\s+(.*)$", stripped)
            if numbered:
                out.append(numbered.group(1).strip())
    return [p for p in out if p]


def _merge_gaps(store_gaps: tuple[str, ...], extra: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for item in (*store_gaps, *extra):
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return tuple(out)


def _clip(text: str) -> str:
    if len(text) <= MAX_TOOL_RESULT_CHARS:
        return text
    return text[: MAX_TOOL_RESULT_CHARS - 20] + "\n…[truncated]"
