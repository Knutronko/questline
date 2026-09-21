"""FastMCP adapter tests (requires questline[mcp])."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

pytest.importorskip("mcp")

from questline.core.config import load_settings
from questline.hud.fixtures import seed_fixture_store
from questline.mcp.context import McpContext
from questline.mcp.server import build_server, tool_names
from questline.mcp.service import READ_TOOLS, WRITE_TOOLS


def test_server_registers_prefixed_tools(tmp_path: Path) -> None:
    store = seed_fixture_store(tmp_path / "store.db")
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")
    settings = load_settings(
        config_path=cfg, profile="mock", project_root=tmp_path
    )
    ctx = McpContext(store=store, settings=settings, project_root=tmp_path)
    server = build_server(ctx)
    names = set(tool_names(server))
    for expected in (*READ_TOOLS, *WRITE_TOOLS):
        assert expected in names, f"missing {expected} in {sorted(names)}"
    for optional in (
        "questline_generate_test",
        "questline_unit_gen",
        "questline_run_eval",
    ):
        assert optional in names, f"missing {optional} in {sorted(names)}"
    assert all(n.startswith("questline_") for n in names)
    cap = asyncio.run(server._tool_manager.call_tool("questline_capabilities", {}))
    payload = cap if isinstance(cap, dict) else cap
    if not isinstance(payload, dict) and hasattr(payload, "__iter__"):
        # FastMCP may wrap as content blocks.
        payload = cap
    text = str(payload)
    assert "questline" in text
    assert "not_unity_mcp" in text or "run_store" in text
