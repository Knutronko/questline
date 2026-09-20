"""Incremental persistence for agent tasks (kill at turn N keeps N-1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from questline.ai.agents.task import AgentTask
from questline.core.store import RunStore


def persist_task(
    store: RunStore, task: AgentTask, *, log_line: dict[str, Any] | None = None
) -> Path:
    dest = store.artifacts_dir / "agents" / task.id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "task.json"
    task.artifact_path = str(path)
    payload = task.to_dict()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    if log_line is not None:
        log_path = dest / "log.jsonl"
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(log_line, sort_keys=True, default=str) + "\n")
    store.save_agent_task(
        task_id=task.id,
        kind=task.kind,
        run_id=task.run_id,
        test_id=task.test_id,
        status=task.status,
        verdict=task.verdict,
        cause=task.cause,
        prompt_version=task.prompt_version,
        artifact_path=str(path),
        created_at=task.created_at,
        meta={
            "pending": task.pending,
            "purpose_tag": task.purpose_tag,
            "tool_count": len(task.tool_log),
            "schema_version": task.schema_version,
        },
    )
    return path


def load_task_artifact(path: str | None) -> dict[str, Any] | None:
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
