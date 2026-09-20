"""Framework unit-test generator. Output is a patch; never auto-commits."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from questline.ai.agents.gate import classify_pytest
from questline.ai.agents.kernel import AgentKernel, new_task_id
from questline.ai.agents.persist import persist_task
from questline.ai.agents.prompts import UNIT_GEN_PROMPT, UNIT_GEN_VERSION
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import UNIT_GEN_TOOLS, ToolContext, default_run_pytest
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.core.store import RunStore

PURPOSE_TAG = "agent.unit_gen"


def run_unit_gen(
    store: RunStore,
    *,
    module_path: str,
    router: Any | None = None,
    project_root: Path | None = None,
    max_turns: int = 8,
    task_id: str | None = None,
    run_pytest: Callable[..., dict[str, Any]] | None = None,
    gate_run: Callable[[str], dict[str, Any]] | None = None,
    measure_coverage: bool = False,
) -> AgentTask:
    """Propose tests for a framework module. Patch lands under artifacts/."""
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    task = AgentTask(
        id=task_id or new_task_id("ugen"),
        kind="unit_gen",
        status="running",
        prompt_version=UNIT_GEN_VERSION,
        purpose_tag=PURPOSE_TAG,
        created_at=datetime.now().astimezone().isoformat(),
        evidence=[{"kind": "module", "path": module_path}],
    )
    persist_task(store, task)
    dest = store.artifacts_dir / "agents" / task.id
    dest.mkdir(parents=True, exist_ok=True)
    proposed = dest / "test_proposed.py"
    rel_proposed = str(proposed.relative_to(root)) if _under(proposed, root) else str(proposed)

    ctx = ToolContext(store=store, project_root=root, run_pytest=run_pytest)
    kernel = AgentKernel(
        store,
        router=router,
        ctx=ctx,
        max_turns=max_turns,
        read_only=False,
        purpose_tag=PURPOSE_TAG,
    )
    user = compose_stable_prefix(
        "MODE: UNIT-GEN (patch only; never git commit)",
        f"MODULE: {module_path}",
        f"WRITE_TEST_TO: {rel_proposed}",
        "Read the module, write proposed pytest to WRITE_TEST_TO, then stop.",
        "Reply JSON: verdict/cause/summary/evidence. Gate owns green/red.",
    )
    try:
        system = load_prompt(UNIT_GEN_PROMPT, UNIT_GEN_VERSION)
    except Exception:
        system = "Propose framework unit tests as a patch. Never auto-commit. JSON verdict."
    kernel.run(task, system=system, user=user, tools=UNIT_GEN_TOOLS)

    claim = dict(task.agent_claim or {})
    patch_path = dest / "patch.diff"
    if proposed.is_file():
        patch_path.write_text(
            _unified_new_file(proposed, rel_path=f"tests/test_{Path(module_path).stem}_ai.py"),
            encoding="utf-8",
        )
        task.patch = str(patch_path)
    runner = gate_run or (
        (lambda nid: default_run_pytest(nid, cwd=root))
        if run_pytest is None
        else (lambda nid: run_pytest(nid))
    )
    executed = False
    green = False
    result: dict[str, Any] = {}
    if proposed.is_file():
        result = runner(str(proposed))
        executed, green = classify_pytest(result)
    cov = (
        _coverage_delta(root, module_path, proposed)
        if measure_coverage and proposed.is_file()
        else None
    )
    task.gate = {
        "executed": executed,
        "green": green,
        "accepted": executed,
        "auto_commit": False,
        "patch": str(patch_path) if patch_path.is_file() else None,
        "coverage_delta": cov,
        "agent_claimed": claim.get("verdict"),
        "returncode": result.get("returncode"),
    }
    if executed:
        task.verdict = "passed" if green else "diagnosed"
        task.status = "ok"
    else:
        task.verdict = "inconclusive"
        task.status = "ok"
        task.summary = (
            (task.summary or "") + " Gate: proposed unit tests did not execute."
        ).strip()
    persist_task(store, task)
    return task


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _unified_new_file(path: Path, *, rel_path: str) -> str:
    body = path.read_text(encoding="utf-8", errors="replace")
    lines = body.splitlines()
    chunks = [f"--- /dev/null\n+++ b/{rel_path}\n@@ -0,0 +1,{len(lines)} @@\n"]
    chunks.extend(f"+{line}\n" for line in lines)
    return "".join(chunks)


def _coverage_delta(root: Path, module_path: str, proposed: Path) -> dict[str, Any] | None:
    """Best-effort coverage of the target module while running the proposed file."""
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(proposed),
                "--tb=no",
                "-q",
                f"--cov={module_path}",
                "--cov-report=term",
                "-o",
                "addopts=",
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (proc.stdout or "") + (proc.stderr or "")
    pct: float | None = None
    for line in text.splitlines():
        if "TOTAL" in line:
            parts = line.split()
            for part in reversed(parts):
                if part.endswith("%"):
                    try:
                        pct = float(part.rstrip("%"))
                    except ValueError:
                        pct = None
                    break
    if pct is None:
        return None
    return {
        "total_percent": pct,
        "note": "absolute coverage of proposed file run, not a delta vs baseline",
    }
