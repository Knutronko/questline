"""Allow-listed DTOs for MCP (no raw home paths, no secrets)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from questline.ai.agents.persist import load_task_artifact
from questline.core.store import RunStore
from questline.hud.queries import allowlisted_artifact
from questline.lens.browse import public_path

_MAX_LIMIT = 100
_ARTIFACT_TEXT_CAP = 64_000


def clamp_limit(limit: int | None, *, default: int = 20, max_n: int = _MAX_LIMIT) -> int:
    n = default if limit is None else int(limit)
    return max(1, min(n, max_n))


def ok(**payload: Any) -> dict[str, Any]:
    return {"ok": True, **payload}


def err(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error": code, "message": message, **extra}


def display_path(path: Path | str | None, root: Path) -> str | None:
    """Relative to project root when possible; otherwise basename only."""
    if path is None:
        return None
    raw = Path(path)
    try:
        return str(raw.resolve().relative_to(root.resolve()))
    except (ValueError, OSError):
        return raw.name


def is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def artifact_public(store: RunStore, payload: dict[str, Any]) -> dict[str, Any]:
    row = allowlisted_artifact(payload)
    row.pop("path", None)
    raw = payload.get("path")
    if isinstance(raw, str) and raw:
        row["artifact"] = public_path(store, raw)
        row["name"] = Path(raw.replace("\\", "/")).name
    return row


def task_public(
    store: RunStore, row: dict[str, Any], *, include_body: bool = False
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.get("id"),
        "kind": row.get("kind"),
        "run_id": row.get("run_id"),
        "test_id": row.get("test_id"),
        "status": row.get("status"),
        "verdict": row.get("verdict"),
        "cause": row.get("cause"),
        "prompt_version": row.get("prompt_version"),
        "created_at": row.get("created_at"),
        "artifact": public_path(store, row.get("artifact_path")),
    }
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    out["pending"] = meta.get("pending")
    out["tool_count"] = meta.get("tool_count")
    if include_body:
        body = load_task_artifact(row.get("artifact_path"))
        if body:
            out["summary"] = body.get("summary")
            out["clusters"] = body.get("clusters") or []
            out["evidence"] = body.get("evidence") or []
            out["suggestion"] = body.get("suggestion")
            out["gate"] = body.get("gate")
            out["tool_log"] = body.get("tool_log") or []
            out["agent_claim"] = body.get("agent_claim")
        costs = store.list_ai_calls(run_id=str(row.get("run_id") or ""))
        tagged = [c for c in costs if str(c.get("purpose") or "").startswith("agent.")]
        out["ai_calls"] = [
            {
                "provider": c.get("provider"),
                "model": c.get("model"),
                "cost": c.get("cost"),
                "purpose": c.get("purpose"),
                "outcome": c.get("outcome"),
            }
            for c in tagged
        ]
        out["ai_cost_total"] = sum(float(c.get("cost") or 0.0) for c in tagged)
    return out


def read_text_capped(path: Path, *, cap: int = _ARTIFACT_TEXT_CAP) -> dict[str, Any]:
    data = path.read_bytes()
    truncated = len(data) > cap
    blob = data[:cap]
    try:
        text = blob.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {
            "encoding": "binary",
            "size_bytes": len(data),
            "truncated": truncated,
        }
    return {
        "encoding": "utf-8",
        "text": text,
        "size_bytes": len(data),
        "truncated": truncated,
    }
