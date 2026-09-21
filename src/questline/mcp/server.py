"""FastMCP stdio adapter. Importing this module requires questline[mcp]."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from questline.mcp import service
from questline.mcp.context import McpContext
from questline.mcp.optional import register_optional

INSTRUCTIONS = """
You are connected to the Questline framework MCP (run store, triage, GameLens).
This is NOT Unity's unity mcp (Editor play/assets/eval). Load both if needed; do not merge.

Hard rules:
- Verdicts, death-points, KPIs, and diffs come from tools that read the store.
- Never invent pass/fail/green/red. A model claim is not a gate.
- Heal suggests locators.yaml only; it does not write the file.
- Diagnose fix mode is disabled unless the server was started with --allow-fix.
- Do not ask for API keys, .env values, or absolute home paths.
- generate_test / unit_gen / run_eval appear only when phase-13 is installed.
""".strip()


def build_server(ctx: McpContext) -> FastMCP:
    mcp = FastMCP("questline", instructions=INSTRUCTIONS)
    _register_read(mcp, ctx)
    _register_write(mcp, ctx)
    register_optional(mcp, ctx)
    return mcp


def run_stdio(ctx: McpContext) -> None:  # pragma: no cover - host owns the stdio loop
    """Block on stdin/stdout JSON-RPC. Callers must not print to stdout first."""
    build_server(ctx).run()


def tool_names(server: FastMCP) -> list[str]:
    return sorted(t.name for t in server._tool_manager.list_tools())


def _register_read(mcp: FastMCP, ctx: McpContext) -> None:
    @mcp.tool(name="questline_capabilities")
    def capabilities() -> dict[str, Any]:
        """List tools, write flags, and planned phase-13 generate/eval tools."""
        return service.capabilities(ctx)

    @mcp.tool(name="questline_doctor")
    def doctor() -> dict[str, Any]:
        """Resolved profile (no secrets, no raw home paths)."""
        return service.doctor(ctx)

    @mcp.tool(name="questline_list_runs")
    def list_runs(
        profile: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Recent pytest runs. Counts come from the store."""
        return service.list_runs(ctx, profile=profile, status=status, limit=limit)

    @mcp.tool(name="questline_get_run")
    def get_run(run_id: str) -> dict[str, Any]:
        """One run plus tests and infra/test/authoring split."""
        return service.get_run(ctx, run_id)

    @mcp.tool(name="questline_get_test")
    def get_test(run_id: str, test_id: str) -> dict[str, Any]:
        """Test detail: steps, death-point, allow-listed artifacts."""
        return service.get_test(ctx, run_id, test_id)

    @mcp.tool(name="questline_list_artifacts")
    def list_artifacts(run_id: str, test_id: str | None = None) -> dict[str, Any]:
        """Artifact names/kinds for a run (paths relative to artifacts_dir)."""
        return service.list_artifacts(ctx, run_id, test_id=test_id)

    @mcp.tool(name="questline_read_artifact")
    def read_artifact(artifact: str) -> dict[str, Any]:
        """Read a text artifact by relative path from list/get. Jailed."""
        return service.read_artifact(ctx, artifact)

    @mcp.tool(name="questline_trends")
    def trends(limit: int = 50) -> dict[str, Any]:
        """Pass-rate / duration over recent runs + flakiness board."""
        return service.run_trends(ctx, limit=limit)

    @mcp.tool(name="questline_list_agent_tasks")
    def list_agent_tasks(
        run_id: str | None = None,
        kind: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Persisted triage/diagnose/heal (and later generate) tasks."""
        return service.list_agent_tasks(ctx, run_id=run_id, kind=kind, limit=limit)

    @mcp.tool(name="questline_get_agent_task")
    def get_agent_task(task_id: str) -> dict[str, Any]:
        """One agent task including summary/clusters/gate when present."""
        return service.get_agent_task(ctx, task_id)

    @mcp.tool(name="questline_list_snapshots")
    def list_snapshots(limit: int = 50) -> dict[str, Any]:
        """GameLens balance snapshot ids (config truth)."""
        return service.list_snapshots(ctx, limit=limit)

    @mcp.tool(name="questline_get_snapshot")
    def get_snapshot(key: str) -> dict[str, Any]:
        """Snapshot metadata. Not a retune verdict."""
        return service.get_snapshot(ctx, key)

    @mcp.tool(name="questline_lens_diff")
    def lens_diff(snapshot_a: str, snapshot_b: str) -> dict[str, Any]:
        """Typed config diff plus persisted implications if any."""
        return service.lens_diff(ctx, snapshot_a, snapshot_b)

    @mcp.tool(name="questline_list_implications")
    def list_implications(
        snapshot_id_a: str | None = None,
        snapshot_id_b: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Index of persisted *model reasoning* implication reports."""
        return service.list_implications(
            ctx,
            snapshot_id_a=snapshot_id_a,
            snapshot_id_b=snapshot_id_b,
            limit=limit,
        )

    @mcp.tool(name="questline_get_implications")
    def get_implications(pair_id: str) -> dict[str, Any]:
        """One implications report (model reasoning; gaps stay gaps)."""
        return service.get_implications(ctx, pair_id)

    @mcp.tool(name="questline_list_sessions")
    def list_sessions(
        config_snapshot_id: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Measured telemetry sessions. outcome=lose is play, not a bot fail."""
        return service.list_sessions(
            ctx, config_snapshot_id=config_snapshot_id, limit=limit
        )

    @mcp.tool(name="questline_get_session")
    def get_session(session_id: str) -> dict[str, Any]:
        """One telemetry session summary (measured)."""
        return service.get_session(ctx, session_id)

    @mcp.tool(name="questline_list_balance_turns")
    def list_balance_turns(
        snapshot_id_a: str | None = None,
        snapshot_id_b: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """GameLens Ask turns (priorities only; does not write SOs)."""
        return service.list_balance_turns(
            ctx,
            snapshot_id_a=snapshot_id_a,
            snapshot_id_b=snapshot_id_b,
            limit=limit,
        )

    @mcp.tool(name="questline_get_balance_turn")
    def get_balance_turn(turn_id: str) -> dict[str, Any]:
        """One balance-agent turn body."""
        return service.get_balance_turn(ctx, turn_id)

    @mcp.tool(name="questline_list_locator_pages")
    def list_locator_pages() -> dict[str, Any]:
        """Page names from locators.yaml (for writing tests later)."""
        return service.list_locator_pages(ctx)

    @mcp.tool(name="questline_get_locator_page")
    def get_locator_page(page: str) -> dict[str, Any]:
        """Locators for one page (by/value/scope)."""
        return service.get_locator_page(ctx, page)

    @mcp.tool(name="questline_collect_tests")
    def collect_tests(path: str = ".", limit: int = 200) -> dict[str, Any]:
        """pytest --collect-only under project_root. Not a run verdict."""
        return service.collect_tests(ctx, path=path, limit=limit)


def _register_write(mcp: FastMCP, ctx: McpContext) -> None:
    @mcp.tool(name="questline_run_triage")
    def run_triage(run_id: str) -> dict[str, Any]:
        """Cluster a finished run. Requires --allow-write. Store owns clusters."""
        return service.run_triage(ctx, run_id)

    @mcp.tool(name="questline_run_diagnose")
    def run_diagnose(
        run_id: str,
        test_id: str,
        fix: bool = False,
        flaky_guard: bool = False,
    ) -> dict[str, Any]:
        """Diagnose one test. fix=true needs --allow-fix; pytest gate owns green."""
        return service.run_diagnose(
            ctx, run_id, test_id, fix=fix, flaky_guard=flaky_guard
        )

    @mcp.tool(name="questline_run_heal")
    def run_heal(run_id: str, test_id: str | None = None) -> dict[str, Any]:
        """Suggest a locators.yaml diff. Never writes. Requires --allow-write."""
        return service.run_heal(ctx, run_id, test_id=test_id)

    @mcp.tool(name="questline_run_balance_ask")
    def run_balance_ask(
        snapshot_a: str,
        snapshot_b: str,
        question: str | None = None,
    ) -> dict[str, Any]:
        """GameLens retune *priorities* (model reasoning). Does not write SOs."""
        return service.run_balance_ask(
            ctx, snapshot_a, snapshot_b, question=question
        )
