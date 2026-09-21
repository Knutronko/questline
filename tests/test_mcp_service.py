"""MCP service layer (no SDK required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from questline.core.config import load_settings
from questline.hud.fixtures import ScriptedBalanceProvider, seed_fixture_store
from questline.mcp import service
from questline.mcp.context import McpContext


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    (tmp_path / "questline.toml").write_text(
        '[profile.mock]\ndriver = "mock"\n', encoding="utf-8"
    )
    (tmp_path / "locators.yaml").write_text(
        "pages:\n  MainMenu:\n    play_button:\n      by: id\n      value: main.play\n",
        encoding="utf-8",
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_demo.py").write_text(
        "def test_boot():\n    assert True\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def ctx(project: Path) -> McpContext:
    store = seed_fixture_store(project / "store.db")
    settings = load_settings(
        config_path=project / "questline.toml",
        profile="mock",
        project_root=project,
    )
    context = McpContext(
        store=store,
        settings=settings,
        project_root=project.resolve(),
        llm_provider=ScriptedBalanceProvider(),
    )
    yield context
    store.close()


def test_capabilities_read_only_and_phase13_tools_available(ctx: McpContext) -> None:
    cap = service.capabilities(ctx)
    assert cap["ok"] is True
    assert cap["not_unity_mcp"] is True
    assert cap["allow_write"] is False
    assert "questline_list_runs" in cap["read_tools"]
    assert cap["planned_tools"]["questline_generate_test"] == "available"
    assert cap["planned_tools"]["questline_unit_gen"] == "available"
    assert cap["planned_tools"]["questline_run_eval"] == "available"
    assert "questline_generate_test" in cap["optional_tools"]


def test_list_and_get_run_store_owned(ctx: McpContext) -> None:
    listed = service.list_runs(ctx)
    ids = {r["id"] for r in listed["runs"]}
    assert "run-a" in ids
    detail = service.get_run(ctx, "run-a")
    assert detail["ok"] is True
    assert detail["run"]["failed"] >= 1
    assert detail["banner"]["infra_failures"] >= 1
    missing = service.get_run(ctx, "nope")
    assert missing["ok"] is False
    assert missing["error"] == "not_found"


def test_get_test_death_point_and_artifact(ctx: McpContext) -> None:
    row = service.get_test(ctx, "run-a", "t-infra")
    assert row["ok"] is True
    assert row["test"]["verdict"] == "infra"
    assert row["death_point"]
    arts = service.list_artifacts(ctx, "run-a", test_id="t-locator")
    assert arts["ok"] is True
    names = [a.get("name") for a in arts["artifacts"]]
    assert "hierarchy.json" in names
    rel = arts["artifacts"][0]["artifact"]
    body = service.read_artifact(ctx, rel)
    assert body["ok"] is True
    assert body["encoding"] == "utf-8"
    assert "Play" in body["text"]


def test_read_artifact_jail(ctx: McpContext, tmp_path: Path) -> None:
    sneaky = service.read_artifact(ctx, "..\\..\\secrets.env")
    assert sneaky["ok"] is False
    assert sneaky["error"] == "jail"


def test_locator_pages(ctx: McpContext) -> None:
    pages = service.list_locator_pages(ctx)
    assert pages["ok"] is True
    assert "MainMenu" in pages["pages"]
    page = service.get_locator_page(ctx, "MainMenu")
    assert page["locators"]["play_button"]["value"] == "main.play"


def test_collect_tests_and_jail(ctx: McpContext) -> None:
    collected = service.collect_tests(ctx, path="tests", limit=50)
    assert collected["ok"] is True
    assert any("test_boot" in n for n in collected["nodeids"])
    jailed = service.collect_tests(ctx, path="..")
    assert jailed["ok"] is False
    assert jailed["error"] == "jail"


def test_lens_snapshot_and_diff(ctx: McpContext) -> None:
    snaps = service.list_snapshots(ctx)
    assert snaps["empty"] is False
    diff = service.lens_diff(ctx, "1.0.0", "1.1.0")
    assert diff["ok"] is True
    assert "diff" in diff
    sessions = service.list_sessions(ctx)
    assert sessions["ok"] is True


def test_write_disabled_by_default(ctx: McpContext) -> None:
    out = service.run_triage(ctx, "run-a")
    assert out["error"] == "write_disabled"
    diag = service.run_diagnose(ctx, "run-a", "t-infra")
    assert diag["error"] == "write_disabled"


def test_diagnose_fix_requires_flag(ctx: McpContext) -> None:
    ctx.allow_write = True
    ctx.allow_fix = False
    out = service.run_diagnose(ctx, "run-a", "t-infra", fix=True)
    assert out["error"] == "fix_disabled"


def test_triage_with_fake_provider(ctx: McpContext) -> None:
    ctx.allow_write = True
    out = service.run_triage(ctx, "run-a")
    assert out["ok"] is True, out
    task = out["task"]
    assert task["kind"] == "triage"
    assert task["verdict"] in {"diagnosed", "inconclusive"}
    listed = service.list_agent_tasks(ctx, run_id="run-a")
    assert listed["empty"] is False


def test_doctor_redacts_to_relative(ctx: McpContext) -> None:
    doc = service.doctor(ctx)
    assert doc["ok"] is True
    assert doc["profile"] == "mock"
    assert "Users" not in str(doc["store_db"])
    assert "Users" not in str(doc["project"])


def test_lens_reads_and_session(ctx: McpContext) -> None:
    snap = service.get_snapshot(ctx, "1.0.0")
    assert snap["ok"] is True
    missing = service.get_snapshot(ctx, "no-such")
    assert missing["error"] == "not_found"
    impl = service.list_implications(ctx)
    assert impl["empty"] is False
    pair_id = impl["implications"][0]["id"]
    body = service.get_implications(ctx, pair_id)
    assert body["ok"] is True
    sess = service.get_session(ctx, "sess-joined")
    assert sess["ok"] is True
    assert sess["session"]["outcome"] == "lose"
    turns = service.list_balance_turns(ctx)
    assert turns["empty"] is False
    turn = service.get_balance_turn(ctx, "ba-fixture")
    assert turn["ok"] is True
    assert turn["turn"]["framing_note"]


def test_diagnose_and_heal_with_fake(ctx: McpContext) -> None:
    ctx.allow_write = True
    diag = service.run_diagnose(ctx, "run-a", "t-infra")
    assert diag["ok"] is True, diag
    assert diag["task"]["kind"] == "diagnose"
    heal = service.run_heal(ctx, "run-a", "t-locator")
    assert heal["ok"] is True, heal
    assert heal["task"]["kind"] == "heal"
    ask = service.run_balance_ask(ctx, "1.0.0", "1.1.0", "What should I retune?")
    assert ask["ok"] is True, ask
    got = service.get_agent_task(ctx, diag["task"]["id"])
    assert got["ok"] is True


def test_unknown_ids(ctx: McpContext) -> None:
    assert service.get_test(ctx, "run-a", "missing")["error"] == "not_found"
    assert service.list_artifacts(ctx, "no-run")["error"] == "not_found"
    assert service.get_agent_task(ctx, "nope")["error"] == "not_found"
    assert service.get_session(ctx, "nope")["error"] == "not_found"
    assert service.get_balance_turn(ctx, "nope")["error"] == "not_found"
    assert service.get_locator_page(ctx, "Missing")["ok"] is False
    ctx.allow_write = True
    assert service.run_triage(ctx, "no-run")["error"] == "not_found"


def test_build_router_skips_cursor_cli(project: Path) -> None:
    from questline.mcp.llm import build_mcp_router

    cfg = project / "questline.toml"
    cfg.write_text(
        """
[profile.mix]
driver = "mock"
ai.candidates = ["cursor", "fake"]
[profile.mix.ai.providers.cursor]
kind = "cursor_cli"
[profile.mix.ai.providers.fake]
kind = "fake"
model = "fake-test"
""",
        encoding="utf-8",
    )
    store = seed_fixture_store(project / "router.db")
    settings = load_settings(
        config_path=cfg, profile="mix", project_root=project
    )
    ctx = McpContext(store=store, settings=settings, project_root=project)
    router = build_mcp_router(ctx, "r1")
    assert router is not None
    assert router._providers[0].kind == "fake"
    store.close()
