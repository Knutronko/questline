"""Maintainer agent — diagnose by default; fix is opt-in with anti-false-green gate."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from questline.ai.agents.kernel import AgentKernel, new_task_id
from questline.ai.agents.persist import persist_task
from questline.ai.agents.prompts import MAINTAINER_PROMPT, MAINTAINER_VERSION
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import (
    FIX_TOOLS,
    READONLY_TOOLS,
    ToolContext,
    default_run_pytest,
)
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.core.store import RunStore

PURPOSE_TAG = "agent.maintainer"


def run_maintainer(
    store: RunStore,
    *,
    run_id: str,
    test_id: str,
    router: Any | None = None,
    project_root: Path | None = None,
    locators_path: Path | None = None,
    quarantine_path: Path | None = None,
    fix: bool = False,
    flaky_guard: bool = False,
    max_turns: int = 8,
    task_id: str | None = None,
    run_pytest: Callable[..., dict[str, Any]] | None = None,
    gate_run: Callable[[str], dict[str, Any]] | None = None,
) -> AgentTask:
    test = store.get_test(test_id)
    if test is None or str(test.get("run_id")) != run_id:
        raise KeyError(f"unknown test {test_id} in run {run_id}")
    nodeid = str(test.get("nodeid") or test_id)
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    kind = "fix" if fix else "diagnose"
    task = AgentTask(
        id=task_id or new_task_id("mnt"),
        kind=kind,
        run_id=run_id,
        test_id=test_id,
        status="running",
        prompt_version=MAINTAINER_VERSION,
        purpose_tag=PURPOSE_TAG,
        created_at=datetime.now().astimezone().isoformat(),
        evidence=[
            {
                "kind": "death_point",
                "error_type": test.get("error_type"),
                "error_message": test.get("error_message"),
                "verdict": test.get("verdict"),
            }
        ],
    )
    persist_task(store, task)

    ctx = ToolContext(
        store=store,
        project_root=root,
        run_id=run_id,
        test_id=test_id,
        locators_path=locators_path,
        quarantine_path=quarantine_path or (root / "quarantine.yaml"),
        run_pytest=run_pytest,
    )
    tools = FIX_TOOLS if fix else READONLY_TOOLS
    kernel = AgentKernel(
        store,
        router=router,
        ctx=ctx,
        max_turns=max_turns,
        read_only=not fix,
        purpose_tag=PURPOSE_TAG,
    )
    if fix:
        mode = "FIX (write_file/run_test allowed; gate still re-runs)"
    else:
        mode = "DIAGNOSE-ONLY (read-only)"
    user = compose_stable_prefix(
        f"MODE: {mode}",
        f"RUN_ID: {run_id}",
        f"TEST_ID: {test_id}",
        f"NODEID: {nodeid}",
        f"STORE VERDICT: {test.get('verdict')} STATUS: {test.get('status')}",
        f"ERROR: {test.get('error_type')} — {test.get('error_message')}",
        "Screenshot-first: call read_screenshot before hierarchy_snapshot.",
        "Reply JSON: verdict in {diagnosed,fixed,inconclusive,passed}, "
        "cause in {test-bug,game-bug,infra,flaky,unknown}, evidence, summary. "
        "Do not claim the test is green; the gate owns that.",
    )
    try:
        system = load_prompt(MAINTAINER_PROMPT, MAINTAINER_VERSION)
    except Exception:
        system = (
            "You are Questline maintainer. Screenshot-first. Never invent green/red. "
            "JSON verdict/cause/evidence/summary."
        )
    kernel.run(task, system=system, user=user, tools=tools)

    claim = dict(task.agent_claim or {})
    if not fix:
        if task.verdict == "fixed":
            # Diagnose must not accept a fix claim.
            task.verdict = "diagnosed"
            persist_task(store, task)
        return task

    runner = gate_run or (
        (lambda nid: default_run_pytest(nid, cwd=root))
        if run_pytest is None
        else (lambda nid: run_pytest(nid))
    )
    first = runner(nodeid)
    repeats = [first]
    if flaky_guard and first.get("green"):
        repeats.append(runner(nodeid))
    all_green = all(bool(r.get("green")) for r in repeats)
    task.gate = {
        "runs": [
            {"green": bool(r.get("green")), "returncode": r.get("returncode")}
            for r in repeats
        ],
        "accepted": all_green,
        "agent_claimed": claim.get("verdict"),
    }
    # Agent claim is logged but ignored — the gate owns green/red.
    if all_green:
        task.verdict = "fixed"
        task.cause = task.cause if task.cause and task.cause != "unknown" else "test-bug"
        task.status = "ok"
    else:
        task.verdict = "inconclusive"
        task.status = "ok"
        task.summary = (
            (task.summary or "")
            + " Gate re-run was red; agent claim ignored."
        ).strip()
    persist_task(store, task)
    return task
