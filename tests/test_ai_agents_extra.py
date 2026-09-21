"""Extra coverage for phase-12 tools, digest, schema, HUD 404s."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from questline.ai.agents.digest import emit_triage_digest, render_digest_text
from questline.ai.agents.healer import (
    flatten_hierarchy,
    rank_candidates,
    run_healer,
    suggested_yaml_diff,
)
from questline.ai.agents.kernel import AgentKernel, _clip, new_task_id
from questline.ai.agents.persist import load_task_artifact, persist_task
from questline.ai.agents.schema import extract_json, parse_agent_output
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import (
    GREP_SCOPED,
    HIERARCHY_SNAPSHOT,
    PROPOSE_QUARANTINE,
    READ_FILE,
    READ_SCREENSHOT,
    RUN_SHELL,
    RUN_TEST,
    STORE_QUERY,
    WRITE_FILE,
    ToolContext,
    ToolSpec,
    clip,
    default_run_pytest,
    jail_path,
    looks_like_write_command,
    parse_args,
    schemas_for,
)
from questline.ai.port import ToolCall
from questline.ai.providers.fake import FakeProvider
from questline.ai.router import ProviderRouter
from questline.core.config import Settings
from questline.core.events import EventBus, RunStarted, TestFinished, TestStarted
from questline.core.store import RunStore
from questline.drivers.locators import Locator, LocatorStrategy
from questline.hud.ai_router import build_hud_router
from questline.hud.fixtures import seed_fixture_store
from questline.reporters.html import HtmlReporter
from questline.reporters.port import RunSummary
from questline.reporters.slack import FakeSlackTransport, SlackReporter


def test_schema_extract_variants() -> None:
    assert extract_json("no json here") is None
    assert extract_json("{not json") is None
    assert extract_json("[1, 2]") is None
    fenced = parse_agent_output('```json\n{"verdict":"diagnosed","cause":"infra"}\n```')
    assert fenced["verdict"] == "diagnosed"
    assert fenced["cause"] == "infra"
    raw = parse_agent_output('{"verdict":"nope","cause":"zzz"}')
    assert raw["verdict"] == "inconclusive"
    assert raw["cause"] == "unknown"
    rich = parse_agent_output(
        '{"verdict":"fixed","cause":"test-bug","evidence":["a"],'
        '"clusters":[{"bucket":"x"}],'
        '"suggestion":{"writes":false},"patch":"diff"}'
    )
    assert rich["verdict"] == "fixed"
    assert rich["evidence"] == ["a"]
    assert rich["clusters"][0]["bucket"] == "x"
    assert rich["suggestion"]["writes"] is False
    assert rich["patch"] == "diff"


def test_load_task_artifact_missing(tmp_path: Path) -> None:
    assert load_task_artifact(None) is None
    assert load_task_artifact(str(tmp_path / "nope.json")) is None
    bad = tmp_path / "x.json"
    bad.write_text("not-json", encoding="utf-8")
    assert load_task_artifact(str(bad)) is None
    listed = tmp_path / "arr.json"
    listed.write_text("[1]", encoding="utf-8")
    assert load_task_artifact(str(listed)) is None


def test_tools_read_grep_write_jail(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        ctx = ToolContext(store=store, project_root=tmp_path)
        (tmp_path / "ok.py").write_text("hello_agent = 1\n", encoding="utf-8")
        (tmp_path / ".env").write_text("SECRET=1\n", encoding="utf-8")
        (tmp_path / "key.pem").write_text("nope\n", encoding="utf-8")
        assert jail_path(ctx, ".env") is None
        assert jail_path(ctx, "") is None
        assert jail_path(ctx, "key.pem") is None
        assert jail_path(ctx, str(Path("/tmp/outside.txt"))) is None
        denied = READ_FILE.handler(ctx, {"path": ".env"})
        assert "error" in denied
        missing = READ_FILE.handler(ctx, {"path": "missing.py"})
        assert "error" in missing
        ok = READ_FILE.handler(ctx, {"path": "ok.py"})
        assert "hello_agent" in ok["content"]
        hits = GREP_SCOPED.handler(ctx, {"pattern": "hello_agent", "path": "."})
        assert hits["hits"]
        file_hits = GREP_SCOPED.handler(ctx, {"pattern": "hello_agent", "path": "ok.py"})
        assert file_hits["hits"]
        bad_pat = GREP_SCOPED.handler(ctx, {"pattern": "["})
        assert "error" in bad_pat
        empty = GREP_SCOPED.handler(ctx, {"pattern": ""})
        assert "error" in empty
        written = WRITE_FILE.handler(ctx, {"path": "out.txt", "content": "x"})
        assert written["ok"] is True
        denied_write = WRITE_FILE.handler(ctx, {"path": ".env", "content": "x"})
        assert "error" in denied_write
        shell = RUN_SHELL.handler(ctx, {"command": "echo hi > pwn.txt"})
        assert "error" in shell
        disabled = RUN_SHELL.handler(ctx, {"command": "echo hi"})
        assert disabled["error"] == "run_shell is not enabled"
        assert looks_like_write_command("Set-Content foo")
        assert looks_like_write_command("") is False
        assert parse_args("{") == {}
        assert parse_args("[]") == {}
        assert parse_args("") == {}
        q = PROPOSE_QUARANTINE.handler(
            ctx,
            {
                "test_id": "t.py::test_x",
                "reason": "flake",
                "owner": "qa",
                "exit_criteria": "green twice",
                "issue": "ISSUE-1",
            },
        )
        assert q["ok"] is True
        no_id = PROPOSE_QUARANTINE.handler(ctx, {})
        assert "error" in no_id
        assert clip("short") == "short"
        assert "truncated" in clip("x" * 9000)
        schemas = schemas_for([WRITE_FILE, READ_FILE], read_only=True)
        assert all(s["function"]["name"] != "write_file" for s in schemas)
    finally:
        store.close()


def test_store_query_screenshot_hierarchy(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    bus = EventBus()
    store.attach(bus)
    try:
        bus.publish(RunStarted(run_id="r1", profile="mock"))
        bus.publish(TestStarted(run_id="r1", test_id="t1", nodeid="t.py::test_a"))
        bus.publish(
            TestFinished(
                run_id="r1",
                test_id="t1",
                nodeid="t.py::test_a",
                status="failed",
                error_type="ElementNotFoundError",
                error_message="not found: id=main.play",
            )
        )
        shot = store.save_artifact(
            b"png", run_id="r1", test_id="t1", name="fail.png", kind="screenshot"
        )
        hier = store.save_artifact(
            b'{"roots":[]}',
            run_id="r1",
            test_id="t1",
            name="hierarchy.json",
            kind="hierarchy",
        )
        ctx = ToolContext(store=store, project_root=tmp_path, run_id="r1", test_id="t1")
        missing_run = STORE_QUERY.handler(ctx, {"run_id": ""})
        ctx2 = ToolContext(store=store, project_root=tmp_path)
        assert "error" in STORE_QUERY.handler(ctx2, {})
        unknown = STORE_QUERY.handler(ctx, {"run_id": "nope"})
        assert "error" in unknown
        payload = STORE_QUERY.handler(ctx, {"run_id": "r1", "test_id": "t1"})
        assert payload["test"]["id"] == "t1"
        assert payload["artifacts"]
        shot_res = READ_SCREENSHOT.handler(ctx, {})
        assert shot_res["attached"] is True
        named = READ_SCREENSHOT.handler(
            ToolContext(store=store, project_root=tmp_path),
            {"path": str(shot.relative_to(tmp_path))},
        )
        assert named["attached"] is True
        empty_store = RunStore(tmp_path / "empty.db", artifacts_dir=tmp_path / "empty-art")
        empty_ctx = ToolContext(store=empty_store, project_root=tmp_path)
        assert "error" in READ_SCREENSHOT.handler(empty_ctx, {})
        assert "error" in READ_SCREENSHOT.handler(empty_ctx, {"path": "missing.png"})
        assert "error" in READ_SCREENSHOT.handler(empty_ctx, {"path": ".env"})
        hier_res = HIERARCHY_SNAPSHOT.handler(ctx, {})
        assert "snapshot" in hier_res
        named_h = HIERARCHY_SNAPSHOT.handler(ctx, {"path": str(hier)})
        assert named_h["snapshot"]["roots"] == []
        bad = tmp_path / "bad.json"
        bad.write_text("{", encoding="utf-8")
        assert "error" in HIERARCHY_SNAPSHOT.handler(ctx, {"path": "bad.json"})
        assert "error" in HIERARCHY_SNAPSHOT.handler(empty_ctx, {})
        assert "error" in HIERARCHY_SNAPSHOT.handler(empty_ctx, {"path": ".env"})
        empty_store.close()
        missing_test = STORE_QUERY.handler(ctx, {"run_id": "r1", "test_id": "missing"})
        assert "test" not in missing_test
        assert payload["run"]["id"] == "r1"
        assert "error" in missing_run or payload is not None
    finally:
        store.close()


def test_run_test_tool(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        ctx = ToolContext(store=store, project_root=tmp_path)
        assert "error" in RUN_TEST.handler(ctx, {})
        ctx.run_pytest = lambda nodeid: {"green": True, "nodeid": nodeid}
        ok = RUN_TEST.handler(ctx, {"nodeid": "t.py::test_x"})
        assert ok["green"] is True
        assert ok["tool"] == "run_test"
        (tmp_path / "tiny_test.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8"
        )
        ctx.run_pytest = None
        via_default = RUN_TEST.handler(ctx, {"nodeid": "tiny_test.py::test_ok"})
        assert via_default["green"] is True
    finally:
        store.close()


def test_default_run_pytest_green_and_red(tmp_path: Path) -> None:
    (tmp_path / "tiny_test.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (tmp_path / "tiny_fail.py").write_text("def test_no():\n    assert False\n", encoding="utf-8")
    green = default_run_pytest("tiny_test.py::test_ok", cwd=tmp_path, timeout_s=30)
    assert green["green"] is True
    red = default_run_pytest("tiny_fail.py::test_no", cwd=tmp_path, timeout_s=30)
    assert red["green"] is False


def test_kernel_skipped_without_router(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        ctx = ToolContext(store=store, project_root=tmp_path)
        kernel = AgentKernel(store, router=None, ctx=ctx, read_only=True)
        task = AgentTask(id="skip", kind="diagnose")
        kernel.run(task, system="s", user="u", tools=())
        assert task.status == "skipped"
        assert task.pending == "no-provider"
        assert new_task_id("ag").startswith("ag-")
        assert "truncated" in _clip("x" * 9000)
    finally:
        store.close()


def test_kernel_llm_error_and_unknown_tool(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        ctx = ToolContext(store=store, project_root=tmp_path)

        class BoomRouter:
            def complete(self, _req: Any) -> Any:
                raise RuntimeError("llm down")

        boom_k = AgentKernel(store, router=BoomRouter(), ctx=ctx, read_only=True)
        boom_task = AgentTask(id="llm", kind="diagnose")
        boom_k.run(boom_task, system="s", user="u", tools=())
        assert boom_task.status == "error"

        fake = FakeProvider()
        fake.enqueue_tools(ToolCall(id="1", name="nope", arguments="{}"))
        fake.enqueue('{"verdict":"inconclusive","cause":"unknown"}')
        kernel = AgentKernel(
            store,
            router=ProviderRouter(
                [fake],
                budget_per_call_usd=10,
                budget_per_run_usd=10,
                store=store,
                run_id="r",
            ),
            ctx=ctx,
            read_only=True,
        )
        task = AgentTask(id="unk", kind="diagnose")
        kernel.run(task, system="s", user="u", tools=(READ_FILE,))
        assert task.tool_log[0]["ok"] is False
        assert task.tool_log[0]["name"] == "nope"

        fake2 = FakeProvider()
        fake2.enqueue('{"verdict":"diagnosed","cause":"infra","summary":"ok"}')
        k2 = AgentKernel(
            store,
            router=ProviderRouter(
                [fake2],
                budget_per_call_usd=10,
                budget_per_run_usd=10,
                store=store,
                run_id="r2",
            ),
            ctx=ctx,
            read_only=True,
        )
        t2 = AgentTask(id="batch", kind="triage")
        out = k2.run_batch([(t2, "s", "u", ())])
        assert out[0].status == "ok"
    finally:
        store.close()


def test_digest_html_and_slack(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        task = AgentTask(
            id="d1",
            kind="triage",
            run_id="r1",
            verdict="diagnosed",
            cause="infra",
            summary="two groups",
            clusters=[
                {
                    "bucket": "infra",
                    "error_type": "X",
                    "test_ids": ["a"],
                    "hypothesis": "h",
                    "signature": "sig",
                }
            ],
        )
        html_rep = HtmlReporter(output_dir=tmp_path / "html")
        fake = FakeSlackTransport()
        settings = Settings.model_validate(
            {
                "profile": "ci",
                "driver": "mock",
                "slack_webhook": "https://example.invalid/hook",
            }
        )
        slack = SlackReporter(settings=settings, transport=fake)

        class BoomReporter:
            def on_event(self, _event: Any) -> None:
                return None

            def finalize(self, _summary: RunSummary) -> None:
                raise RuntimeError("reporter boom")

        class OkReporter:
            def __init__(self) -> None:
                self.seen = False

            def on_event(self, _event: Any) -> None:
                return None

            def finalize(self, _summary: RunSummary) -> None:
                self.seen = True

        ok_rep = OkReporter()
        emit_triage_digest(
            task, store=store, reporters=[html_rep, slack, BoomReporter(), ok_rep]
        )
        assert (tmp_path / "html" / "triage-r1.html").is_file()
        assert fake.webhooks or fake.messages
        assert ok_rep.seen is True
        assert "two groups" in render_digest_text(task)
        persist_task(store, task, log_line={"turn": 1, "name": "store_query", "ok": True})
        log = tmp_path / "art" / "agents" / "d1" / "log.jsonl"
        assert log.is_file()

        bot_settings = Settings.model_validate({"profile": "ci", "slack_token": "tok"})
        bot = SlackReporter(settings=bot_settings, transport=FakeSlackTransport())
        emit_triage_digest(task, store=store, reporters=[bot])
        bot._start_ts = "1.0"
        bot._channel = "C1"
        emit_triage_digest(task, store=store, reporters=[bot])
    finally:
        store.close()


def test_healer_helpers() -> None:
    snap = {
        "roots": [
            {
                "element": {"id": "a", "name": "A", "path": "/A", "text": "t"},
                "children": [{"element": {"id": "b", "name": "B", "path": "/A/B", "text": ""}}],
            }
        ]
    }
    nodes = flatten_hierarchy(snap)
    assert any(n["id"] == "b" for n in nodes)
    assert flatten_hierarchy([{"id": "x", "name": "X", "path": "/x", "text": ""}])
    assert flatten_hierarchy(None) == []
    assert flatten_hierarchy("nope") == []
    ranked = rank_candidates("B", nodes, by="name")
    assert ranked[0]["id"] == "b"
    by_path = rank_candidates("/A/B", nodes, by="path")
    assert by_path[0]["value"]
    by_text = rank_candidates("t", nodes, by="text")
    assert by_text
    diff = suggested_yaml_diff(
        page="P",
        name="n",
        old=Locator(by=LocatorStrategy.ID, value="old"),
        new_by="id",
        new_value="new",
    )
    assert "old" in diff and "new" in diff
    empty = suggested_yaml_diff(
        page="P", name="n", old=None, new_by="id", new_value="x"
    )
    assert "?" in empty


def test_healer_keyerror_without_locator_fail(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        with pytest.raises(KeyError, match="no ElementNotFound"):
            run_healer(store, run_id="missing")
        bus = EventBus()
        store.attach(bus)
        bus.publish(RunStarted(run_id="r1", profile="mock"))
        bus.publish(TestStarted(run_id="r1", test_id="t1", nodeid="t.py::ok"))
        bus.publish(TestFinished(run_id="r1", test_id="t1", nodeid="t.py::ok", status="passed"))
        with pytest.raises(KeyError):
            run_healer(store, run_id="r1")
        with pytest.raises(KeyError, match="unknown test"):
            run_healer(store, run_id="r1", test_id="nope")
        (tmp_path / "locators.yaml").write_text("not: valid: yaml: [", encoding="utf-8")
        bus.publish(TestStarted(run_id="r1", test_id="loc", nodeid="t.py::loc"))
        bus.publish(
            TestFinished(
                run_id="r1",
                test_id="loc",
                nodeid="t.py::loc",
                status="failed",
                error_type="ElementNotFoundError",
                error_message="not found: id=gone",
            )
        )
        task = run_healer(
            store,
            run_id="r1",
            test_id="loc",
            project_root=tmp_path,
            locators_path=tmp_path / "locators.yaml",
        )
        assert task.suggestion is not None
        assert task.suggestion["writes"] is False
    finally:
        store.close()


def test_hud_agent_404s(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from questline.hud.server import create_app

    store = seed_fixture_store(tmp_path / "s.db")
    try:
        app = create_app(store=store, project_root=tmp_path)
        with TestClient(app) as client:
            token = client.get("/api/csrf").json()["csrf_token"]
            headers = {"x-csrf-token": token}
            missing = client.post(
                "/api/agents/triage",
                json={"run_id": "nope"},
                headers=headers,
            )
            assert missing.status_code == 404
            listed = client.get("/api/runs/nope/agent-tasks")
            assert listed.status_code == 404
            detail = client.get("/api/agent-tasks/missing")
            assert detail.status_code == 404
            diag = client.post(
                "/api/agents/diagnose",
                json={"run_id": "x", "test_id": "y"},
                headers=headers,
            )
            assert diag.status_code == 404
            heal_run = client.post(
                "/api/agents/heal",
                json={"run_id": "nope"},
                headers=headers,
            )
            assert heal_run.status_code == 404
            heal_empty = client.post(
                "/api/agents/heal",
                json={"run_id": "run-b"},
                headers=headers,
            )
            assert heal_empty.status_code == 404
    finally:
        store.close()


def test_build_hud_router_injected_and_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        fake = FakeProvider()
        injected = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(llm_provider=fake))
        )
        router = build_hud_router(injected, store, None, run_id="r")
        assert router is not None

        missing_cfg = tmp_path / "missing.toml"
        none_req = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    llm_provider=None,
                    config_path=missing_cfg,
                    project_root=tmp_path,
                )
            )
        )
        assert build_hud_router(none_req, store, "ai_groq", run_id="r") is None

        cfg = tmp_path / "questline.toml"
        cfg.write_text(
            """
[profile.ai_groq]
driver = "mock"
ai.candidates = ["cli", "oa_nokey", "oa_nomodel", "oa", "ollama", "fake", "ghost"]
[profile.ai_groq.ai.providers.cli]
kind = "cursor_cli"
[profile.ai_groq.ai.providers.oa_nokey]
kind = "openai_compat"
base_url = "https://example.invalid"
model = "m"
api_key_env = "QL_TEST_NO_KEY"
[profile.ai_groq.ai.providers.oa_nomodel]
kind = "openai_compat"
api_key_env = "QL_TEST_KEY"
[profile.ai_groq.ai.providers.oa]
kind = "openai_compat"
base_url = "https://example.invalid"
model = "m"
api_key_env = "QL_TEST_KEY"
[profile.ai_groq.ai.providers.ollama]
kind = "ollama"
model = "llama3.2"
[profile.ai_groq.ai.providers.fake]
kind = "fake"
model = "fake-test"
""",
            encoding="utf-8",
        )
        monkeypatch.setenv("QL_TEST_KEY", "not-a-real-secret")
        monkeypatch.delenv("QL_TEST_NO_KEY", raising=False)
        live = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    llm_provider=None,
                    config_path=cfg,
                    project_root=tmp_path,
                )
            )
        )
        built = build_hud_router(live, store, "ai_groq", run_id="r")
        assert built is not None

        empty_cfg = tmp_path / "empty.toml"
        empty_cfg.write_text('[profile.ai_groq]\ndriver = "mock"\n', encoding="utf-8")
        empty_req = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    llm_provider=None,
                    config_path=empty_cfg,
                    project_root=tmp_path,
                )
            )
        )
        assert build_hud_router(empty_req, store, "ai_groq", run_id="r") is None
    finally:
        store.close()


def test_build_hud_router_env_groq_when_game_toml_has_no_ai(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ElJuegaso-style toml: editor only. GROQ_API_KEY in the HUD process is enough."""
    monkeypatch.setenv("GROQ_API_KEY", "test-not-a-real-key")
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:
        cfg = tmp_path / "questline.toml"
        cfg.write_text(
            '[profile.editor]\ndriver = "questline"\ntarget_platform = "editor"\n',
            encoding="utf-8",
        )
        req = SimpleNamespace(
            app=SimpleNamespace(
                state=SimpleNamespace(
                    llm_provider=None,
                    config_path=cfg,
                    project_root=tmp_path,
                )
            )
        )
        built = build_hud_router(req, store, None, run_id="r")
        assert built is not None
        names = [p.name for p in built._providers]
        assert names[0] == "groq"
        assert "ollama" in names
    finally:
        store.close()


def test_kernel_handler_exception(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    try:

        def boom(_ctx: ToolContext, _args: dict) -> dict:
            raise RuntimeError("tool boom")

        spec = ToolSpec(
            name="boom",
            description="x",
            parameters={"type": "object", "properties": {}},
            handler=boom,
        )
        fake = FakeProvider()
        fake.enqueue_tools(ToolCall(id="1", name="boom", arguments="{}"))
        fake.enqueue('{"verdict":"inconclusive","cause":"unknown"}')
        ctx = ToolContext(store=store, project_root=tmp_path)
        kernel = AgentKernel(
            store,
            router=ProviderRouter(
                [fake],
                budget_per_call_usd=10,
                budget_per_run_usd=10,
                store=store,
                run_id="r",
            ),
            ctx=ctx,
            read_only=True,
        )
        task = AgentTask(id="boom", kind="diagnose")
        kernel.run(task, system="s", user="u", tools=(spec,))
        assert task.tool_log[0]["ok"] is False

        def huge(_ctx: ToolContext, _args: dict) -> dict:
            return {"blob": "x" * 9000}

        spec2 = ToolSpec(
            name="huge",
            description="x",
            parameters={"type": "object", "properties": {}},
            handler=huge,
        )
        fake2 = FakeProvider()
        fake2.enqueue_tools(ToolCall(id="1", name="huge", arguments="{}"))
        fake2.enqueue('{"verdict":"inconclusive","cause":"unknown"}')
        k2 = AgentKernel(
            store,
            router=ProviderRouter(
                [fake2],
                budget_per_call_usd=10,
                budget_per_run_usd=10,
                store=store,
                run_id="r2",
            ),
            ctx=ctx,
            read_only=True,
        )
        t2 = AgentTask(id="huge", kind="diagnose")
        k2.run(t2, system="s", user="u", tools=(spec2,))
        assert t2.status in {"ok", "truncated"}
    finally:
        store.close()
