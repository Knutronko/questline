"""MCP tool implementations. Store owns numbers; models do not invent verdicts."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from typing import Any

from questline import __version__
from questline.core.errors import AuthoringError
from questline.core.store import RunStore
from questline.drivers.locators import load_locators
from questline.hud.queries import enrich_run, enrich_test, test_history_sparkline, trends
from questline.lens.browse import (
    SnapshotNotFoundError,
    diff_from_store,
    implications_for_pair,
    implications_payload,
    implications_row_public,
    list_sessions_public,
    list_snapshots_public,
    public_path,
    resolve_snapshot_row,
    session_public,
    snapshot_row_public,
)
from questline.mcp.context import McpContext
from questline.mcp.dto import (
    artifact_public,
    clamp_limit,
    display_path,
    err,
    is_under,
    ok,
    read_text_capped,
    task_public,
)

READ_TOOLS = (
    "questline_capabilities",
    "questline_doctor",
    "questline_list_runs",
    "questline_get_run",
    "questline_get_test",
    "questline_list_artifacts",
    "questline_read_artifact",
    "questline_trends",
    "questline_list_agent_tasks",
    "questline_get_agent_task",
    "questline_list_snapshots",
    "questline_get_snapshot",
    "questline_lens_diff",
    "questline_list_implications",
    "questline_get_implications",
    "questline_list_sessions",
    "questline_get_session",
    "questline_list_balance_turns",
    "questline_get_balance_turn",
    "questline_list_locator_pages",
    "questline_get_locator_page",
    "questline_collect_tests",
)

WRITE_TOOLS = (
    "questline_run_triage",
    "questline_run_diagnose",
    "questline_run_heal",
    "questline_run_balance_ask",
)

PLANNED_TOOLS = (
    "questline_generate_test",
    "questline_unit_gen",
    "questline_run_eval",
)


def module_available(dotted: str) -> bool:
    try:
        return importlib.util.find_spec(dotted) is not None
    except (ModuleNotFoundError, ValueError):
        return False


def planned_status() -> dict[str, str]:
    mapping = {
        "questline_generate_test": "questline.ai.agents.generator",
        "questline_unit_gen": "questline.ai.agents.unit_gen",
        "questline_run_eval": "questline.evalharness.runner",
    }
    return {
        name: ("available" if module_available(mod) else "planned")
        for name, mod in mapping.items()
    }


def capabilities(ctx: McpContext) -> dict[str, Any]:
    """What this server can do in this process (not a Unity MCP)."""
    planned = planned_status()
    write = list(WRITE_TOOLS)
    optional = [name for name, state in planned.items() if state == "available"]
    return ok(
        server="questline",
        version=__version__,
        data_plane="run_store",
        not_unity_mcp=True,
        allow_write=ctx.allow_write,
        allow_fix=ctx.allow_fix,
        read_tools=list(READ_TOOLS),
        write_tools=write,
        optional_tools=optional,
        planned_tools=planned,
        notes=(
            "Verdicts and KPIs come from the store. "
            "Do not treat model text as green/red. "
            "unity mcp is a different server (Editor). "
            "generate/eval tools appear after phase-13 is installed."
        ),
    )


def doctor(ctx: McpContext) -> dict[str, Any]:
    settings = ctx.settings
    wait = settings.wait
    mcp_extra = "installed" if module_available("mcp") else "missing"
    return ok(
        questline=__version__,
        profile=settings.profile,
        driver=settings.driver or None,
        reporters=list(settings.reporters),
        project=display_path(settings.project_root, ctx.project_root),
        store_db=display_path(settings.store_db, ctx.project_root),
        artifacts=display_path(settings.artifacts_dir, ctx.project_root),
        wait={
            "probe": wait.probe,
            "deadline": wait.deadline,
            "interval": wait.interval,
        },
        ai_candidates=list(settings.ai.candidates),
        mcp_extra=mcp_extra,
        allow_write=ctx.allow_write,
        allow_fix=ctx.allow_fix,
    )


def list_runs(
    ctx: McpContext,
    *,
    profile: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    rows = ctx.store.list_runs(
        profile=profile or None,
        status=status or None,
        limit=clamp_limit(limit),
        offset=0,
    )
    runs = [enrich_run(ctx.store, r) for r in rows]
    return ok(runs=runs, empty=len(runs) == 0)


def get_run(ctx: McpContext, run_id: str) -> dict[str, Any]:
    run = ctx.store.get_run(run_id)
    if run is None:
        return err("not_found", f"run not found: {run_id}")
    tests = [enrich_test(ctx.store, t) for t in ctx.store.list_tests(run_id)]
    enriched = enrich_run(ctx.store, run)
    return ok(
        run=enriched,
        tests=tests,
        banner={
            "infra_failures": enriched["infra_failures"],
            "test_failures": enriched["test_failures"],
            "authoring_failures": enriched["authoring_failures"],
            "unknown_failures": enriched["unknown_failures"],
        },
    )


def get_test(ctx: McpContext, run_id: str, test_id: str) -> dict[str, Any]:
    test = ctx.store.get_test(test_id)
    if test is None or str(test.get("run_id")) != run_id:
        return err("not_found", f"test not found: {test_id}")
    steps = ctx.store.list_steps(test_id)
    death = ctx.store.death_point(test_id)
    artifacts = [
        artifact_public(ctx.store, a)
        for a in ctx.store.list_artifacts(run_id=run_id, test_id=test_id)
    ]
    history = test_history_sparkline(ctx.store, str(test.get("nodeid") or ""))
    return ok(
        test=enrich_test(ctx.store, test),
        steps=steps,
        death_point=death,
        artifacts=artifacts,
        history=history,
    )


def list_artifacts(ctx: McpContext, run_id: str, test_id: str | None = None) -> dict[str, Any]:
    if ctx.store.get_run(run_id) is None:
        return err("not_found", f"run not found: {run_id}")
    rows = ctx.store.list_artifacts(run_id=run_id, test_id=test_id or None)
    return ok(artifacts=[artifact_public(ctx.store, a) for a in rows])


def read_artifact(ctx: McpContext, artifact: str) -> dict[str, Any]:
    """Read a text artifact under artifacts_dir (relative path from list/get)."""
    rel = artifact.replace("\\", "/").lstrip("/")
    target = (ctx.store.artifacts_dir / rel).resolve()
    if not is_under(target, ctx.store.artifacts_dir):
        return err("jail", "artifact path must stay under artifacts_dir")
    if not target.is_file():
        return err("not_found", f"artifact not found: {rel}")
    payload = read_text_capped(target)
    payload["artifact"] = public_path(ctx.store, str(target))
    payload["name"] = target.name
    return ok(**payload)


def run_trends(ctx: McpContext, limit: int = 50) -> dict[str, Any]:
    return ok(**trends(ctx.store, limit_runs=clamp_limit(limit, default=50)))


def list_agent_tasks(
    ctx: McpContext,
    *,
    run_id: str | None = None,
    kind: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    rows = ctx.store.list_agent_tasks(
        run_id=run_id or None,
        kind=kind or None,
        limit=clamp_limit(limit),
    )
    return ok(
        tasks=[task_public(ctx.store, r, include_body=True) for r in rows],
        empty=len(rows) == 0,
    )


def get_agent_task(ctx: McpContext, task_id: str) -> dict[str, Any]:
    row = ctx.store.get_agent_task(task_id)
    if row is None:
        return err("not_found", f"agent task not found: {task_id}")
    return ok(task=task_public(ctx.store, row, include_body=True))


def list_snapshots(ctx: McpContext, limit: int = 50) -> dict[str, Any]:
    rows = list_snapshots_public(ctx.store, limit=clamp_limit(limit, default=50))
    return ok(snapshots=rows, empty=len(rows) == 0)


def get_snapshot(ctx: McpContext, key: str) -> dict[str, Any]:
    try:
        row = resolve_snapshot_row(ctx.store, key)
    except SnapshotNotFoundError as exc:
        return err("not_found", f"snapshot not found: {exc}")
    return ok(snapshot=snapshot_row_public(ctx.store, row))


def lens_diff(ctx: McpContext, snapshot_a: str, snapshot_b: str) -> dict[str, Any]:
    try:
        report = diff_from_store(ctx.store, snapshot_a, snapshot_b)
    except SnapshotNotFoundError as exc:
        return err("not_found", f"snapshot not found: {exc}")
    except AuthoringError as exc:
        return err("invalid", str(exc))
    return ok(
        diff=report.to_dict(),
        implications=implications_for_pair(ctx.store, snapshot_a, snapshot_b),
        framing="diff is measured config; implications are model reasoning when present",
    )


def list_implications(
    ctx: McpContext,
    *,
    snapshot_id_a: str | None = None,
    snapshot_id_b: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    rows = ctx.store.list_lens_implications(
        snapshot_id_a=snapshot_id_a or None,
        snapshot_id_b=snapshot_id_b or None,
        limit=clamp_limit(limit, default=50),
    )
    return ok(
        implications=[implications_row_public(ctx.store, row) for row in rows],
        empty=len(rows) == 0,
    )


def get_implications(ctx: McpContext, pair_id: str) -> dict[str, Any]:
    payload = implications_payload(ctx.store, pair_id)
    if payload is None:
        return err("not_found", f"implications not found: {pair_id}")
    return ok(implications=payload)


def list_sessions(
    ctx: McpContext,
    *,
    config_snapshot_id: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    rows = list_sessions_public(
        ctx.store,
        config_snapshot_id=config_snapshot_id or None,
        limit=clamp_limit(limit, default=50),
    )
    return ok(sessions=rows, empty=len(rows) == 0)


def get_session(ctx: McpContext, session_id: str) -> dict[str, Any]:
    row = ctx.store.get_telemetry_session(session_id)
    if row is None:
        return err("not_found", f"session not found: {session_id}")
    payload = session_public(row, include_summary=True)
    payload["event_count"] = ctx.store.count_telemetry_events(str(row["id"]))
    return ok(session=payload)


def list_balance_turns(
    ctx: McpContext,
    *,
    snapshot_id_a: str | None = None,
    snapshot_id_b: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    rows = ctx.store.list_lens_agent_turns(
        snapshot_id_a=snapshot_id_a or None,
        snapshot_id_b=snapshot_id_b or None,
        limit=clamp_limit(limit),
    )
    return ok(
        turns=[_turn_public(ctx.store, row) for row in rows],
        empty=len(rows) == 0,
    )


def get_balance_turn(ctx: McpContext, turn_id: str) -> dict[str, Any]:
    row = ctx.store.get_lens_agent_turn(turn_id)
    if row is None:
        return err("not_found", f"agent turn not found: {turn_id}")
    return ok(turn=_turn_public(ctx.store, row, include_body=True))


def list_locator_pages(ctx: McpContext) -> dict[str, Any]:
    path = ctx.locators_file()
    if not path.is_file():
        return err("not_found", "locators.yaml not found at project root")
    try:
        registry = load_locators(path)
    except AuthoringError as exc:
        return err("invalid", str(exc))
    return ok(pages=registry.pages())


def get_locator_page(ctx: McpContext, page: str) -> dict[str, Any]:
    path = ctx.locators_file()
    if not path.is_file():
        return err("not_found", "locators.yaml not found at project root")
    try:
        registry = load_locators(path)
        locs = registry.locators_for(page)
    except AuthoringError as exc:
        return err("invalid", str(exc))
    payload = {
        name: {
            "by": loc.by.value if hasattr(loc.by, "value") else str(loc.by),
            "value": loc.value,
            "scope": loc.scope,
        }
        for name, loc in locs.items()
    }
    return ok(page=page, locators=payload)


def collect_tests(
    ctx: McpContext, path: str = ".", limit: int = 200
) -> dict[str, Any]:
    """pytest --collect-only jailed to project_root. Does not execute tests."""
    root = ctx.project_root.resolve()
    rel = (path or ".").strip() or "."
    target = root if rel in {".", ""} else (root / rel).resolve()
    if not is_under(target, root):
        return err("jail", "collect path must stay under project_root")
    argv = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        "-o",
        "addopts=",
        "--rootdir",
        str(root),
        "--confcutdir",
        str(root),
        str(target),
    ]
    try:
        proc = subprocess.run(
            argv,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return err("timeout", "pytest collect timed out")
    nodeids: list[str] = []
    cap = clamp_limit(limit, default=200, max_n=2000)
    for line in (proc.stdout or "").splitlines():
        text = line.strip()
        if "::" in text and not text.startswith("="):
            nodeids.append(text)
            if len(nodeids) >= cap:
                break
    return ok(
        nodeids=nodeids,
        returncode=proc.returncode,
        truncated=len(nodeids) >= cap,
        hint="collect-only; not a run verdict",
    )


def _write_guard(ctx: McpContext) -> dict[str, Any] | None:
    if ctx.allow_write:
        return None
    return err(
        "write_disabled",
        "Restart the MCP server with `questline mcp --allow-write` to invoke agents.",
    )


def _router(ctx: McpContext, run_id: str) -> Any | None:
    from questline.mcp.llm import build_mcp_router

    return build_mcp_router(ctx, run_id)


def _need_router(ctx: McpContext, run_id: str) -> Any | dict[str, Any]:
    router = _router(ctx, run_id)
    if router is None:
        return err(
            "no_llm",
            "No LLM provider configured for this MCP process. "
            "Use --allow-write with a profile that has keys, or inject a fake in tests.",
        )
    return router


def run_triage(ctx: McpContext, run_id: str) -> dict[str, Any]:
    blocked = _write_guard(ctx)
    if blocked:
        return blocked
    if ctx.store.get_run(run_id) is None:
        return err("not_found", f"run not found: {run_id}")
    from questline.ai.agents.triage import run_triage as _run

    router = _need_router(ctx, run_id)
    if isinstance(router, dict):
        return router
    task = _run(
        ctx.store,
        run_id=run_id,
        router=router,
        project_root=ctx.project_root,
    )
    row = ctx.store.get_agent_task(task.id)
    if row is None:
        return err("persist", "agent task did not persist")
    return ok(task=task_public(ctx.store, row, include_body=True))


def run_diagnose(
    ctx: McpContext,
    run_id: str,
    test_id: str,
    *,
    fix: bool = False,
    flaky_guard: bool = False,
) -> dict[str, Any]:
    blocked = _write_guard(ctx)
    if blocked:
        return blocked
    if fix and not ctx.allow_fix:
        return err(
            "fix_disabled",
            "Diagnose --fix requires `questline mcp --allow-fix`. "
            "The pytest gate still owns green.",
        )
    if ctx.store.get_test(test_id) is None:
        return err("not_found", f"test not found: {test_id}")
    from questline.ai.agents.maintainer import run_maintainer

    router = _need_router(ctx, run_id)
    if isinstance(router, dict):
        return router
    task = run_maintainer(
        ctx.store,
        run_id=run_id,
        test_id=test_id,
        router=router,
        project_root=ctx.project_root,
        quarantine_path=ctx.project_root / "quarantine.yaml",
        fix=fix,
        flaky_guard=flaky_guard,
    )
    row = ctx.store.get_agent_task(task.id)
    if row is None:
        return err("persist", "agent task did not persist")
    return ok(task=task_public(ctx.store, row, include_body=True))


def run_heal(ctx: McpContext, run_id: str, test_id: str | None = None) -> dict[str, Any]:
    blocked = _write_guard(ctx)
    if blocked:
        return blocked
    if ctx.store.get_run(run_id) is None:
        return err("not_found", f"run not found: {run_id}")
    from questline.ai.agents.healer import run_healer

    router = _need_router(ctx, run_id)
    if isinstance(router, dict):
        return router
    try:
        task = run_healer(
            ctx.store,
            run_id=run_id,
            test_id=test_id,
            router=router,
            project_root=ctx.project_root,
            locators_path=ctx.locators_file(),
        )
    except KeyError as exc:
        return err("not_found", str(exc))
    row = ctx.store.get_agent_task(task.id)
    if row is None:
        return err("persist", "agent task did not persist")
    return ok(task=task_public(ctx.store, row, include_body=True))


def run_balance_ask(
    ctx: McpContext,
    snapshot_a: str,
    snapshot_b: str,
    question: str | None = None,
) -> dict[str, Any]:
    blocked = _write_guard(ctx)
    if blocked:
        return blocked
    from questline.lens.agent import load_turn_artifact, run_balance_agent

    router = _need_router(ctx, "mcp-balance")
    if isinstance(router, dict):
        return router
    try:
        diff_from_store(ctx.store, snapshot_a, snapshot_b)
    except SnapshotNotFoundError as exc:
        return err("not_found", f"snapshot not found: {exc}")
    except AuthoringError as exc:
        return err("invalid", str(exc))
    turn = run_balance_agent(
        ctx.store,
        snapshot_a=snapshot_a,
        snapshot_b=snapshot_b,
        question=question,
        router=router,
    )
    row = ctx.store.get_lens_agent_turn(turn.id)
    if row is None:
        return err("persist", "balance turn did not persist")
    return ok(turn=_turn_public(ctx.store, row, include_body=True, loader=load_turn_artifact))


def _turn_public(
    store: RunStore,
    row: dict[str, Any],
    *,
    include_body: bool = False,
    loader: Any | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.get("id"),
        "snapshot_id_a": row.get("snapshot_id_a"),
        "snapshot_id_b": row.get("snapshot_id_b"),
        "question": row.get("question"),
        "status": row.get("status"),
        "framing": row.get("framing"),
        "prompt_version": row.get("prompt_version"),
        "created_at": row.get("created_at"),
        "artifact": public_path(store, row.get("artifact_path")),
    }
    meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
    out["pending"] = meta.get("pending")
    out["gap_count"] = meta.get("gap_count")
    out["tool_count"] = meta.get("tool_count")
    if include_body:
        load = loader
        if load is None:
            from questline.lens.agent import load_turn_artifact as load
        body = load(row.get("artifact_path"))
        if body:
            out["summary"] = body.get("summary")
            out["priorities"] = body.get("priorities") or []
            out["gaps"] = body.get("gaps") or []
            out["citations"] = body.get("citations") or {}
            out["tool_log"] = body.get("tool_log") or []
        out["framing_note"] = "model reasoning; not measured KPIs"
    return out
