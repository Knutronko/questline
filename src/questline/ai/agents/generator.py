"""Spec → scenario test. Success is owned by the pytest execution gate."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from questline.ai.agents.gate import classify_pytest, expected_from_spec, spec_matches
from questline.ai.agents.kernel import AgentKernel, new_task_id
from questline.ai.agents.persist import persist_task
from questline.ai.agents.prompts import GENERATOR_PROMPT, GENERATOR_VERSION
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import GENERATOR_TOOLS, ToolContext, clip
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.core.store import RunStore

PURPOSE_TAG = "agent.generator"


def run_generator(
    store: RunStore,
    *,
    spec: str,
    dest: Path,
    router: Any | None = None,
    project_root: Path | None = None,
    run_id: str | None = None,
    rebuild_test_id: str | None = None,
    max_turns: int = 8,
    task_id: str | None = None,
    run_pytest: Callable[..., dict[str, Any]] | None = None,
    gate_run: Callable[[str], dict[str, Any]] | None = None,
) -> AgentTask:
    """Write a test from *spec*. Gate must execute pytest before success."""
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    out_dir = Path(dest)
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    expected = expected_from_spec(spec)
    history = _rebuild_history(store, rebuild_test_id) if rebuild_test_id else ""
    task = AgentTask(
        id=task_id or new_task_id("gen"),
        kind="generate",
        run_id=run_id,
        test_id=rebuild_test_id,
        status="running",
        prompt_version=GENERATOR_VERSION,
        purpose_tag=PURPOSE_TAG,
        created_at=datetime.now().astimezone().isoformat(),
        evidence=[{"kind": "spec", "text": spec[:2000], "expected": expected}],
    )
    persist_task(store, task)

    ctx = ToolContext(
        store=store,
        project_root=root,
        run_id=run_id,
        test_id=rebuild_test_id,
        run_pytest=run_pytest,
    )
    kernel = AgentKernel(
        store,
        router=router,
        ctx=ctx,
        max_turns=max_turns,
        read_only=False,
        purpose_tag=PURPOSE_TAG,
    )
    user = compose_stable_prefix(
        "MODE: GENERATE",
        f"OUTPUT_DIR: {out_dir}",
        f"EXPECTED_OUTCOME: {expected}",
        f"PROJECT_ROOT: {root}",
        "Write a pytest file under OUTPUT_DIR using existing pages/locators.",
        "Unknown locators: TODO + pytest.fail, never a silent pass.",
        "Reply JSON: verdict/cause/summary/evidence. Do not claim green; the gate owns that.",
        f"REBUILD_HISTORY:\n{history}" if history else "REBUILD_HISTORY: (none)",
        f"SPEC:\n{spec}",
    )
    try:
        system = load_prompt(GENERATOR_PROMPT, GENERATOR_VERSION)
    except Exception:
        system = (
            "You generate Questline tests from a spec. Never invent green/red. "
            "JSON verdict/cause/evidence/summary."
        )
    kernel.run(task, system=system, user=user, tools=GENERATOR_TOOLS)

    claim = dict(task.agent_claim or {})
    written = _written_pytest_paths(task, out_dir, root)
    runner = gate_run or (
        (lambda nid: _generate_run_pytest(nid, cwd=root))
        if run_pytest is None
        else (lambda nid: run_pytest(nid))
    )
    if not written:
        task.gate = {
            "executed": False,
            "accepted": False,
            "expected": expected,
            "reason": "no pytest file written",
            "agent_claimed": claim.get("verdict"),
        }
        task.verdict = "inconclusive"
        task.status = "ok"
        task.summary = (
            (task.summary or "") + " Gate: no generated test file to execute."
        ).strip()
        persist_task(store, task)
        return task

    nodeid = str(written[0])
    result = runner(nodeid)
    executed, green = classify_pytest(result)
    accepted = spec_matches(expected, executed=executed, green=green)
    task.gate = {
        "executed": executed,
        "green": green,
        "expected": expected,
        "accepted": accepted,
        "nodeid": nodeid,
        "returncode": result.get("returncode"),
        "agent_claimed": claim.get("verdict"),
        "stdout_tail": str(result.get("stdout") or "")[-500:],
    }
    if accepted:
        task.verdict = "passed" if green else "diagnosed"
        task.cause = task.cause if task.cause and task.cause != "unknown" else "test-bug"
        task.status = "ok"
    else:
        task.verdict = "inconclusive"
        task.status = "ok"
        task.summary = (
            (task.summary or "")
            + " Gate: generated test did not execute as specified; agent claim ignored."
        ).strip()
    persist_task(store, task)
    return task


def _generate_run_pytest(nodeid: str, *, cwd: Path) -> dict[str, Any]:
    """Pytest with questline.toml when present so generated authoring tests collect."""
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        nodeid,
        "--tb=line",
        "-q",
        "-p",
        "no:cov",
        "-o",
        "addopts=",
        "--rootdir",
        str(cwd),
    ]
    cfg = cwd / "questline.toml"
    if cfg.is_file():
        cmd.extend(
            ["--questline-config", str(cfg), "--questline-profile", "mock"]
        )
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=60.0,
        check=False,
    )
    return {
        "nodeid": nodeid,
        "returncode": proc.returncode,
        "green": proc.returncode == 0,
        "stdout": clip((proc.stdout or "")[-4000:]),
        "stderr": clip((proc.stderr or "")[-2000:]),
    }


def _written_pytest_paths(task: AgentTask, out_dir: Path, root: Path) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for entry in task.tool_log:
        if entry.get("name") != "write_file" or not entry.get("ok"):
            continue
        raw = (entry.get("arguments") or {}).get("path")
        if not raw:
            continue
        for candidate in (
            Path(str(raw)),
            root / str(raw),
            out_dir / Path(str(raw)).name,
        ):
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved.suffix != ".py" or not resolved.is_file() or resolved in seen:
                continue
            seen.add(resolved)
            found.append(resolved)
    if found:
        return found
    if out_dir.is_dir():
        return sorted(p for p in out_dir.glob("test_*.py") if p.is_file())
    return []


def _rebuild_history(store: RunStore, test_id: str) -> str:
    rows = store.list_agent_tasks(test_id=test_id, kind="generate", limit=5)
    if not rows:
        tests = store.get_test(test_id)
        if tests:
            return (
                f"store test {test_id} status={tests.get('status')} "
                f"error={tests.get('error_type')} {tests.get('error_message')}"
            )
        return f"no prior generate tasks for {test_id}"
    lines = []
    for row in rows:
        lines.append(
            f"{row.get('created_at')} verdict={row.get('verdict')} "
            f"status={row.get('status')} cause={row.get('cause')}"
        )
    return "\n".join(lines)
