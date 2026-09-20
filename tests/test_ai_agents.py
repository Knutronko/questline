"""Phase-12 agent kernel + triage / maintainer / healer (scripted FakeProvider)."""

from __future__ import annotations

import json
from pathlib import Path

from questline.ai.agents.healer import rank_candidates, run_healer
from questline.ai.agents.kernel import AgentKernel, new_task_id
from questline.ai.agents.maintainer import run_maintainer
from questline.ai.agents.task import AgentTask
from questline.ai.agents.tools import (
    READONLY_TOOLS,
    RUN_SHELL,
    WRITE_FILE,
    ToolContext,
    looks_like_write_command,
)
from questline.ai.agents.triage import cluster_failures, run_triage
from questline.ai.port import ToolCall
from questline.ai.providers.fake import FakeProvider
from questline.ai.router import ProviderRouter
from questline.core.events import EventBus, RunFinished, RunStarted, TestFinished, TestStarted
from questline.core.store import RunStore
from questline.reporters.port import ReporterPort, RunSummary


def _router(fake: FakeProvider, store: RunStore, run_id: str) -> ProviderRouter:
    return ProviderRouter(
        [fake],
        budget_per_call_usd=10.0,
        budget_per_run_usd=10.0,
        store=store,
        run_id=run_id,
    )


def _seed_failures(store: RunStore, *, n_infra: int = 3, n_loc: int = 2) -> str:
    bus = EventBus()
    store.attach(bus)
    rid = "run-fail"
    bus.publish(RunStarted(run_id=rid, profile="mock"))
    for i in range(n_infra):
        tid = f"infra-{i}"
        bus.publish(TestStarted(run_id=rid, test_id=tid, nodeid=f"t.py::test_infra_{i}"))
        bus.publish(
            TestFinished(
                run_id=rid,
                test_id=tid,
                nodeid=f"t.py::test_infra_{i}",
                status="failed",
                verdict="infra",
                error_type="SessionLostError",
                error_message="socket closed 13000",
            )
        )
    for i in range(n_loc):
        tid = f"loc-{i}"
        bus.publish(TestStarted(run_id=rid, test_id=tid, nodeid=f"t.py::test_loc_{i}"))
        bus.publish(
            TestFinished(
                run_id=rid,
                test_id=tid,
                nodeid=f"t.py::test_loc_{i}",
                status="failed",
                verdict="test",
                error_type="ElementNotFoundError",
                error_message="not found: id=main.play",
            )
        )
    bus.publish(RunFinished(run_id=rid, status="failed"))
    return rid


def test_looks_like_write_command() -> None:
    assert looks_like_write_command("echo pwn > x.txt")
    assert looks_like_write_command("rm -rf dest")
    assert not looks_like_write_command("pytest tests/foo.py -q")


def test_kernel_per_task_budget_does_not_starve_batch(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    fake = FakeProvider()
    fake.enqueue_tools(ToolCall(id="t", name="store_query", arguments="{}"))
    fake.enqueue_tools(ToolCall(id="t2", name="store_query", arguments="{}"))
    fake.enqueue(
        json.dumps({"verdict": "diagnosed", "cause": "unknown", "summary": "task-b"})
    )
    ctx = ToolContext(store=store, project_root=tmp_path)
    kernel = AgentKernel(
        store, router=_router(fake, store, "batch"), ctx=ctx, max_turns=2, read_only=True
    )
    a = AgentTask(id="a", kind="diagnose", run_id="r")
    b = AgentTask(id="b", kind="diagnose", run_id="r")
    user = "done"
    results = kernel.run_batch(
        [
            (a, "sys", user, READONLY_TOOLS),
            (b, "sys", user, READONLY_TOOLS),
        ]
    )
    assert results[0].status == "truncated"
    assert results[0].pending == "max-turns"
    assert results[1].status == "ok"
    assert results[1].summary == "task-b"


def test_kill_at_turn_n_preserves_n_minus_1(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    fake = FakeProvider()
    fake.enqueue_tools(ToolCall(id="1", name="store_query", arguments="{}"))
    fake.enqueue(RuntimeError("killed at turn 2"))
    ctx = ToolContext(store=store, project_root=tmp_path)
    kernel = AgentKernel(
        store, router=_router(fake, store, "k"), ctx=ctx, max_turns=5, read_only=True
    )
    task = AgentTask(id="kill-me", kind="diagnose", run_id="r")
    kernel.run(task, system="s", user="u", tools=READONLY_TOOLS)
    assert task.status == "error"
    assert len(task.tool_log) == 1
    row = store.get_agent_task("kill-me")
    assert row is not None
    body = json.loads(Path(row["artifact_path"]).read_text(encoding="utf-8"))
    assert len(body["tool_log"]) == 1
    log = (tmp_path / "art" / "agents" / "kill-me" / "log.jsonl").read_text(encoding="utf-8")
    assert log.strip().count("\n") + 1 == 1


def test_hermetic_read_only_blocks_write_tools(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    target = tmp_path / "pwn.txt"
    fake = FakeProvider()
    fake.enqueue_tools(
        ToolCall(
            id="1",
            name="write_file",
            arguments=json.dumps({"path": str(target), "content": "pwn"}),
        )
    )
    fake.enqueue_tools(
        ToolCall(id="2", name="run_shell", arguments=json.dumps({"command": "echo pwn > pwn.txt"}))
    )
    fake.enqueue(json.dumps({"verdict": "diagnosed", "cause": "unknown", "summary": "no write"}))
    ctx = ToolContext(store=store, project_root=tmp_path)
    kernel = AgentKernel(
        store, router=_router(fake, store, "ro"), ctx=ctx, max_turns=5, read_only=True
    )
    task = AgentTask(id="ro", kind="diagnose", run_id="r")
    kernel.run(
        task,
        system="s",
        user="write the file",
        tools=(*READONLY_TOOLS, WRITE_FILE, RUN_SHELL),
    )
    assert not target.exists()
    names = [e["name"] for e in task.tool_log]
    assert "write_file" in names
    assert "run_shell" in names
    assert any("error" in json.dumps(e) or e.get("ok") is False for e in task.tool_log)


def test_false_green_rejected_when_gate_red(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    bus = EventBus()
    store.attach(bus)
    bus.publish(RunStarted(run_id="r1", profile="mock"))
    bus.publish(TestStarted(run_id="r1", test_id="t1", nodeid="seed.py::test_x"))
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="t1",
            nodeid="seed.py::test_x",
            status="failed",
            verdict="test",
            error_type="AssertionFailedError",
            error_message="1 == 2",
        )
    )
    fake = FakeProvider()
    fake.enqueue_tools(ToolCall(id="1", name="store_query", arguments="{}"))
    fake.enqueue(
        json.dumps({"verdict": "fixed", "cause": "test-bug", "summary": "I fixed it"})
    )

    def gate(_nodeid: str) -> dict:
        return {"green": False, "returncode": 1}

    task = run_maintainer(
        store,
        run_id="r1",
        test_id="t1",
        router=_router(fake, store, "r1"),
        project_root=tmp_path,
        fix=True,
        gate_run=gate,
    )
    assert task.verdict == "inconclusive"
    assert task.agent_claim and task.agent_claim.get("verdict") == "fixed"
    assert task.gate and task.gate["accepted"] is False


def test_fix_accepted_only_when_gate_green(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    bus = EventBus()
    store.attach(bus)
    bus.publish(RunStarted(run_id="r1", profile="mock"))
    bus.publish(TestStarted(run_id="r1", test_id="t1", nodeid="seed.py::test_x"))
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="t1",
            nodeid="seed.py::test_x",
            status="failed",
            verdict="test",
            error_type="AssertionFailedError",
            error_message="boom",
        )
    )
    fake = FakeProvider()
    fake.enqueue(
        json.dumps({"verdict": "fixed", "cause": "test-bug", "summary": "patched"})
    )
    calls = {"n": 0}

    def gate(_nodeid: str) -> dict:
        calls["n"] += 1
        return {"green": True, "returncode": 0}

    task = run_maintainer(
        store,
        run_id="r1",
        test_id="t1",
        router=_router(fake, store, "r1"),
        project_root=tmp_path,
        fix=True,
        flaky_guard=True,
        gate_run=gate,
    )
    assert task.verdict == "fixed"
    assert calls["n"] == 2
    rows = store.list_ai_calls(run_id="r1")
    assert any(str(r.get("purpose") or "").startswith("agent.") for r in rows)


def test_triage_clusters_five_failures_into_two_groups(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    rid = _seed_failures(store)
    clusters = cluster_failures(store.list_tests(rid))
    assert len(clusters) >= 2
    sizes = sorted(len(c["test_ids"]) for c in clusters)
    assert sizes[-2:] == [2, 3]
    fake = FakeProvider()
    fake.enqueue_tools(ToolCall(id="1", name="store_query", arguments="{}"))
    fake.enqueue(
        json.dumps(
            {
                "verdict": "diagnosed",
                "cause": "infra",
                "summary": "infra vs locator",
                "clusters": [
                    {"key": "infra", "hypothesis": "session"},
                    {"key": "loc", "hypothesis": "rename"},
                ],
            }
        )
    )

    class Sink:
        def __init__(self) -> None:
            self.summaries: list[RunSummary] = []

        def on_event(self, _event: object) -> None:
            return None

        def finalize(self, run_summary: RunSummary) -> None:
            self.summaries.append(run_summary)

    sink: ReporterPort = Sink()  # type: ignore[assignment]
    task = run_triage(
        store,
        run_id=rid,
        router=_router(fake, store, rid),
        project_root=tmp_path,
        reporters=[sink],
    )
    assert len(task.clusters) >= 2
    digest = tmp_path / "art" / "agents" / task.id / "digest.html"
    assert digest.is_file()
    assert sink.summaries  # type: ignore[attr-defined]


def test_healer_suggests_renamed_element_never_writes(tmp_path: Path) -> None:
    yaml_path = tmp_path / "locators.yaml"
    yaml_path.write_text(
        "pages:\n  MainMenu:\n    play_button:\n      by: id\n      value: main.play\n",
        encoding="utf-8",
    )
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    bus = EventBus()
    store.attach(bus)
    bus.publish(RunStarted(run_id="r1", profile="mock"))
    bus.publish(TestStarted(run_id="r1", test_id="t1", nodeid="t.py::test_play"))
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="t1",
            nodeid="t.py::test_play",
            status="failed",
            verdict="test",
            error_type="ElementNotFoundError",
            error_message="not found: id=main.play",
        )
    )
    hier = {
        "roots": [
            {
                "element": {
                    "id": "main.play_btn",
                    "name": "PlayButton",
                    "path": "/Canvas/Play",
                    "text": "Play",
                },
                "children": [],
            }
        ]
    }
    store.save_artifact(
        json.dumps(hier).encode("utf-8"),
        run_id="r1",
        test_id="t1",
        name="hierarchy.json",
        kind="hierarchy",
        bus=bus,
    )
    ranked = rank_candidates(
        "main.play",
        [
            {
                "id": "main.play_btn",
                "name": "PlayButton",
                "path": "/Canvas/Play",
                "text": "Play",
                "parent": "",
            }
        ],
    )
    assert ranked[0]["id"] == "main.play_btn"
    fake = FakeProvider()
    fake.enqueue(json.dumps({"verdict": "fixed", "cause": "test-bug", "summary": "write it"}))
    original = yaml_path.read_text(encoding="utf-8")
    task = run_healer(
        store,
        run_id="r1",
        test_id="t1",
        router=_router(fake, store, "r1"),
        project_root=tmp_path,
        locators_path=yaml_path,
    )
    assert yaml_path.read_text(encoding="utf-8") == original
    assert task.verdict == "diagnosed"
    assert task.suggestion and task.suggestion.get("writes") is False
    diff = str(task.suggestion.get("yaml_diff") or "")
    assert "main.play_btn" in diff or "PlayButton" in diff or "main.play" in diff


def test_diagnose_locator_and_assertion_seed(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    bus = EventBus()
    store.attach(bus)
    bus.publish(RunStarted(run_id="r1", profile="mock"))
    bus.publish(TestStarted(run_id="r1", test_id="loc", nodeid="t.py::test_loc"))
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="loc",
            nodeid="t.py::test_loc",
            status="failed",
            verdict="test",
            error_type="ElementNotFoundError",
            error_message="not found: id=main.play",
        )
    )
    bus.publish(TestStarted(run_id="r1", test_id="asn", nodeid="t.py::test_asn"))
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="asn",
            nodeid="t.py::test_asn",
            status="failed",
            verdict="test",
            error_type="AssertionFailedError",
            error_message="coins == 0",
        )
    )
    fake = FakeProvider()
    fake.enqueue(
        json.dumps({"verdict": "diagnosed", "cause": "test-bug", "summary": "bad locator"})
    )
    loc = run_maintainer(
        store,
        run_id="r1",
        test_id="loc",
        router=_router(fake, store, "r1"),
        project_root=tmp_path,
        fix=False,
    )
    fake.enqueue(
        json.dumps({"verdict": "diagnosed", "cause": "test-bug", "summary": "bad assert"})
    )
    asn = run_maintainer(
        store,
        run_id="r1",
        test_id="asn",
        router=_router(fake, store, "r1"),
        project_root=tmp_path,
        fix=False,
    )
    assert loc.verdict == "diagnosed"
    assert asn.verdict == "diagnosed"
    assert loc.cause == "test-bug"


def test_fix_mode_gate_runs_real_pytest(tmp_path: Path) -> None:
    target = tmp_path / "seed_test.py"
    target.write_text("def test_x():\n    assert False\n", encoding="utf-8")
    store = RunStore(tmp_path / "s.db", artifacts_dir=tmp_path / "art")
    bus = EventBus()
    store.attach(bus)
    bus.publish(RunStarted(run_id="r1", profile="mock"))
    bus.publish(TestStarted(run_id="r1", test_id="t1", nodeid="seed_test.py::test_x"))
    bus.publish(
        TestFinished(
            run_id="r1",
            test_id="t1",
            nodeid="seed_test.py::test_x",
            status="failed",
            verdict="test",
            error_type="AssertionFailedError",
            error_message="assert False",
        )
    )
    fake = FakeProvider()
    fake.enqueue_tools(
        ToolCall(
            id="1",
            name="write_file",
            arguments=json.dumps(
                {"path": str(target), "content": "def test_x():\n    assert True\n"}
            ),
        )
    )
    fake.enqueue(json.dumps({"verdict": "fixed", "cause": "test-bug", "summary": "patched"}))
    task = run_maintainer(
        store,
        run_id="r1",
        test_id="t1",
        router=_router(fake, store, "r1"),
        project_root=tmp_path,
        fix=True,
    )
    assert task.verdict == "fixed"
    assert task.gate and task.gate["accepted"] is True
    assert "assert True" in target.read_text(encoding="utf-8")


def test_new_task_id_prefix() -> None:
    assert new_task_id("tri").startswith("tri-")
