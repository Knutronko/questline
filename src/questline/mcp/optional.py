"""Optional phase-13 tools. Missing modules stay `planned` in capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from questline.mcp.context import McpContext
from questline.mcp.dto import err, is_under, ok, task_public
from questline.mcp.service import _need_router, _write_guard, module_available


def register_optional(mcp: Any, ctx: McpContext) -> list[str]:
    """Attach generate/eval tools when those packages exist in this install."""
    names: list[str] = []
    if module_available("questline.ai.agents.generator"):

        @mcp.tool(name="questline_generate_test")
        def generate_test(
            spec: str,
            dest: str | None = None,
            rebuild_test_id: str | None = None,
        ) -> dict[str, Any]:
            """Spec → pytest file (phase-13). Gate owns execute; not a model green."""
            return _generate(ctx, spec, dest=dest, rebuild_test_id=rebuild_test_id)

        names.append("questline_generate_test")

    if module_available("questline.ai.agents.unit_gen"):

        @mcp.tool(name="questline_unit_gen")
        def unit_gen(module_path: str) -> dict[str, Any]:
            """Propose framework unit tests (phase-13). Patch is an artifact, not a commit."""
            return _unit_gen(ctx, module_path)

        names.append("questline_unit_gen")

    if module_available("questline.evalharness.runner"):

        @mcp.tool(name="questline_run_eval")
        def run_eval(
            agent: str = "maintainer",
            provider: str = "fake",
            prompt_version: str = "v1",
        ) -> dict[str, Any]:
            """Run the eval harness (phase-13). Fake provider is the CI path."""
            return _run_eval(
                ctx, agent=agent, provider=provider, prompt_version=prompt_version
            )

        names.append("questline_run_eval")
    return names


def _generate(
    ctx: McpContext,
    spec: str,
    *,
    dest: str | None,
    rebuild_test_id: str | None,
) -> dict[str, Any]:  # pragma: no cover - phase-13 module absent on this branch
    blocked = _write_guard(ctx)
    if blocked:
        return blocked
    from questline.ai.agents.generator import run_generator

    router = _need_router(ctx, "mcp-generate")
    if isinstance(router, dict):
        return router
    root = ctx.project_root
    out = Path(dest) if dest else (root / "generated-tests")
    if not out.is_absolute():
        out = root / out
    if not is_under(out, root):
        return err("jail", "dest must stay under project_root")
    task = run_generator(
        ctx.store,
        spec=spec,
        dest=out,
        router=router,
        project_root=root,
        rebuild_test_id=rebuild_test_id,
    )
    row = ctx.store.get_agent_task(task.id)
    if row is None:
        return err("persist", "generate task did not persist")
    return ok(task=task_public(ctx.store, row, include_body=True))


def _unit_gen(ctx: McpContext, module_path: str) -> dict[str, Any]:  # pragma: no cover
    blocked = _write_guard(ctx)
    if blocked:
        return blocked
    from questline.ai.agents.unit_gen import run_unit_gen

    router = _need_router(ctx, "mcp-unit-gen")
    if isinstance(router, dict):
        return router
    task = run_unit_gen(
        ctx.store,
        module_path=module_path,
        router=router,
        project_root=ctx.project_root,
    )
    row = ctx.store.get_agent_task(task.id)
    if row is None:
        return err("persist", "unit-gen task did not persist")
    return ok(task=task_public(ctx.store, row, include_body=True))


def _run_eval(
    ctx: McpContext,
    *,
    agent: str,
    provider: str,
    prompt_version: str,
) -> dict[str, Any]:  # pragma: no cover
    blocked = _write_guard(ctx)
    if blocked:
        return blocked
    from questline.evalharness.runner import run_eval

    router = None if provider == "fake" else _need_router(ctx, "mcp-eval")
    if isinstance(router, dict):
        return router
    result = run_eval(
        ctx.store,
        agent=agent,
        provider=provider,
        prompt_version=prompt_version,
        router=router,
    )
    if hasattr(result, "to_dict"):
        payload = result.to_dict()
    else:
        payload = {"id": getattr(result, "id", None)}
    return ok(eval=payload, hint="metrics are harness-owned; not a model claim")
