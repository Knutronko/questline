"""Run triage agent — read-only digest of a finished pytest run."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from questline.ai.agents.digest import emit_triage_digest
from questline.ai.agents.kernel import AgentKernel, new_task_id
from questline.ai.agents.persist import persist_task
from questline.ai.agents.prompts import TRIAGE_PROMPT, TRIAGE_VERSION
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import READONLY_TOOLS, ToolContext
from questline.ai.prompts.store import compose_stable_prefix, load_prompt
from questline.core.store import RunStore
from questline.reporters.port import ReporterPort

PURPOSE_TAG = "agent.triage"


def cluster_failures(tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic clusters by error_type + normalized message. Store owns grouping."""
    groups: dict[str, dict[str, Any]] = {}
    for test in tests:
        status = str(test.get("status") or "")
        if status not in {"failed", "error"}:
            continue
        err_type = str(test.get("error_type") or "unknown")
        msg = _normalize_msg(str(test.get("error_message") or ""))
        key = f"{err_type}|{msg}"
        bucket = groups.setdefault(
            key,
            {
                "key": key,
                "error_type": err_type,
                "signature": msg,
                "bucket": _bucket(err_type, test.get("verdict")),
                "test_ids": [],
                "nodeids": [],
            },
        )
        bucket["test_ids"].append(test.get("id"))
        bucket["nodeids"].append(test.get("nodeid"))
    return sorted(groups.values(), key=lambda g: (-len(g["test_ids"]), g["key"]))


def run_triage(
    store: RunStore,
    *,
    run_id: str,
    router: Any | None = None,
    project_root: Path | None = None,
    reporters: list[ReporterPort] | None = None,
    git_diff: str | None = None,
    max_turns: int = 6,
    task_id: str | None = None,
) -> AgentTask:
    run = store.get_run(run_id)
    if run is None:
        raise KeyError(f"unknown run: {run_id}")
    tests = store.list_tests(run_id)
    clusters = cluster_failures(tests)
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    task = AgentTask(
        id=task_id or new_task_id("tri"),
        kind="triage",
        run_id=run_id,
        status="running",
        prompt_version=TRIAGE_VERSION,
        purpose_tag=PURPOSE_TAG,
        created_at=datetime.now().astimezone().isoformat(),
        clusters=clusters,
        evidence=[{"kind": "clusters", "count": len(clusters)}],
        verdict="diagnosed" if clusters else "passed",
        cause="unknown",
    )
    persist_task(store, task)

    ctx = ToolContext(store=store, project_root=root, run_id=run_id)
    kernel = AgentKernel(
        store,
        router=router,
        ctx=ctx,
        max_turns=max_turns,
        read_only=True,
        purpose_tag=PURPOSE_TAG,
    )
    user = compose_stable_prefix(
        f"RUN_ID: {run_id}",
        "DETERMINISTIC CLUSTERS (store-owned; do not invent tests):\n"
        + _fmt_clusters(clusters),
        f"OPTIONAL GIT DIFF:\n{git_diff or '(none)'}",
        "Call store_query if needed. Reply with JSON: verdict, cause, summary, "
        "clusters (same groups; add hypothesis per cluster). Read-only.",
    )
    try:
        system = load_prompt(TRIAGE_PROMPT, TRIAGE_VERSION)
    except Exception:
        system = (
            "You are Questline run triage. Read-only. Cluster failures. "
            "Never invent green/red. JSON: verdict, cause, summary, clusters."
        )
    kernel.run(task, system=system, user=user, tools=READONLY_TOOLS)
    # Store-owned clusters win if the model dropped them.
    if not task.clusters:
        task.clusters = clusters
        persist_task(store, task)
    if clusters and task.verdict == "passed":
        task.verdict = "diagnosed"
        persist_task(store, task)
    emit_triage_digest(task, store=store, reporters=reporters or [])
    return task


def _bucket(error_type: str, verdict: Any) -> str:
    v = str(verdict or "")
    if v == "infra" or "SessionLost" in error_type or "Infra" in error_type:
        return "infra"
    if "ElementNotFound" in error_type or v == "test":
        return "test"
    if "Authoring" in error_type:
        return "test"
    return v or "unknown"


def _normalize_msg(msg: str) -> str:
    text = msg.strip()
    text = _NUM.sub("<n>", text)
    return text[:160] or "(no message)"


_NUM = __import__("re").compile(r"\d+")


def _fmt_clusters(clusters: list[dict[str, Any]]) -> str:
    if not clusters:
        return "(no failures)"
    lines = []
    for c in clusters:
        lines.append(
            f"- {c['bucket']}: {c['error_type']} / {c['signature']} "
            f"({len(c['test_ids'])} tests)"
        )
    return "\n".join(lines)
