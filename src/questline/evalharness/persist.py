"""Persist eval runs to artifacts/eval/<id>/result.json + store index."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from questline.core.store import RunStore
from questline.evalharness.schema import EvalRun


def persist_eval_run(store: RunStore, run: EvalRun) -> Path:
    dest = store.artifacts_dir / "eval" / run.id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "result.json"
    if not run.created_at:
        run.created_at = datetime.now().astimezone().isoformat()
    run.artifact_path = str(path)
    payload = run.to_dict()
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    store.save_eval_result(
        eval_id=run.id,
        agent=run.agent,
        provider=run.provider,
        prompt_version=run.prompt_version,
        status=run.status,
        artifact_path=str(path),
        diagnosis_accuracy=run.diagnosis_accuracy,
        fix_correctness=run.fix_correctness,
        false_green_rate=run.false_green_rate,
        iterations_avg=run.iterations_avg,
        cost_usd=run.cost_usd,
        case_count=run.case_count,
        created_at=run.created_at,
        meta=run.meta,
    )
    return path


def load_eval_artifact(path: str | None) -> dict[str, Any] | None:
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
