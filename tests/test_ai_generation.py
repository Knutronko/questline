"""Phase-13 spec→test generator + unit-gen (scripted FakeProvider + pytest gate)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from questline.ai.agents.canned import CANNED_MOCKDRIVER_TEST, DemoGenerateProvider
from questline.ai.agents.gate import classify_pytest, expected_from_spec
from questline.ai.agents.generator import _generate_run_pytest, run_generator
from questline.ai.agents.unit_gen import run_unit_gen
from questline.ai.errors import RateLimitedError
from questline.ai.port import LlmResponse, ToolCall
from questline.ai.providers.fake import FakeProvider
from questline.ai.router import ProviderRouter
from questline.core.store import RunStore

ROOT = Path(__file__).resolve().parents[1]
VALID_TEST = '''\
"""Generated from spec (MockDriver demo)."""
from pages import HudPage, MainMenuPage
from questline.authoring import expect
from questline.authoring.context import Context
from questline.authoring.markers import quest


@quest.smoke
def test_play_from_spec(questline_ctx: Context) -> None:
    MainMenuPage(questline_ctx).play()
    text = HudPage(questline_ctx).coins_text()
    expect(text).equals("Coins: 100").evaluate()
'''


def _router(fake: FakeProvider, store: RunStore, run_id: str) -> ProviderRouter:
    return ProviderRouter(
        [fake],
        budget_per_call_usd=10.0,
        budget_per_run_usd=10.0,
        store=store,
        run_id=run_id,
    )


def _demo_proj(tmp_path: Path) -> Path:
    proj = tmp_path / "demo_proj"
    proj.mkdir()
    shutil.copy(ROOT / "examples" / "questline.toml", proj / "questline.toml")
    shutil.copytree(ROOT / "examples" / "demo-tests", proj / "demo-tests")
    shutil.copy(ROOT / "examples" / "generated_locators.py", proj / "generated_locators.py")
    scene = ROOT / "examples" / "demo-tests" / "scene.py"
    if scene.is_file():
        shutil.copy(scene, proj / "scene.py")
    return proj


def test_classify_pytest_collection_error_is_not_executed() -> None:
    executed, green = classify_pytest(
        {
            "returncode": 2,
            "stdout": "ERROR collecting test_broken.py\nSyntaxError: invalid syntax\n1 error",
            "stderr": "",
        }
    )
    assert executed is False
    assert green is False
    assert expected_from_spec("expect: red\nTap play.") == "red"
    assert expected_from_spec("just a story") == "green"


def test_generator_gate_rejects_non_executing_file(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    dest = tmp_path / "out"
    dest.mkdir()
    fake = FakeProvider()
    fake.enqueue_tools(
        ToolCall(
            id="w1",
            name="write_file",
            arguments=json.dumps(
                {"path": str(dest / "test_broken.py"), "content": "this is not python {{{"}
            ),
        )
    )
    fake.enqueue(
        json.dumps({"verdict": "passed", "cause": "unknown", "summary": "I claim green"})
    )
    task = run_generator(
        store,
        spec="expect: green\nTap play.",
        dest=dest,
        router=_router(fake, store, "g1"),
        project_root=tmp_path,
        run_id="g1",
    )
    assert task.gate is not None
    assert task.gate["executed"] is False
    assert task.gate["accepted"] is False
    assert task.verdict == "inconclusive"
    assert task.gate.get("agent_claimed") == "passed"
    store.close()


def test_generator_five_line_spec_runs_mockdriver(tmp_path: Path) -> None:
    proj = _demo_proj(tmp_path)
    dest = proj / "demo-tests"
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    out_file = dest / "test_from_spec.py"
    fake = FakeProvider()
    fake.enqueue_tools(
        ToolCall(
            id="w1",
            name="write_file",
            arguments=json.dumps({"path": str(out_file), "content": VALID_TEST}),
        )
    )
    fake.enqueue(json.dumps({"verdict": "passed", "cause": "unknown", "summary": "wrote test"}))
    spec = (ROOT / "examples" / "specs" / "buy_pack.md").read_text(encoding="utf-8")
    task = run_generator(
        store,
        spec=spec,
        dest=dest,
        router=_router(fake, store, "g2"),
        project_root=proj,
        run_id="g2",
    )
    assert task.gate is not None
    assert task.gate["executed"] is True, task.gate
    assert task.gate["green"] is True
    assert task.gate["accepted"] is True
    assert task.verdict == "passed"
    store.close()


def test_canned_mockdriver_test_executes(tmp_path: Path) -> None:
    dest = tmp_path / "generated-tests"
    dest.mkdir()
    path = dest / "test_from_spec.py"
    path.write_text(CANNED_MOCKDRIVER_TEST, encoding="utf-8")
    result = _generate_run_pytest(str(path), cwd=tmp_path)
    executed, green = classify_pytest(result)
    assert executed is True, result
    assert green is True


def test_demo_generate_provider_writes_and_gates(tmp_path: Path) -> None:
    dest = tmp_path / "generated-tests"
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    task = run_generator(
        store,
        spec="When the player taps Play, HUD coins show 100.\nexpect: green",
        dest=dest,
        router=_router(DemoGenerateProvider(), store, "g-demo"),
        project_root=tmp_path,
        run_id="g-demo",
    )
    assert task.gate is not None
    assert task.gate["executed"] is True, task.gate
    assert task.gate["accepted"] is True
    assert task.gate.get("mock_driver") is True
    nodeid = str(task.gate["nodeid"])
    assert "test_gen_" in nodeid
    assert (tmp_path / nodeid).is_file()
    store.close()


def test_collect_gate_with_pages_layout(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages" / "__init__.py").write_text(
        "class SmokePage:\n    def ping(self) -> str:\n        return 'pong'\n",
        encoding="utf-8",
    )
    (tmp_path / "locators.yaml").write_text("pages: {}\n", encoding="utf-8")
    dest = tmp_path / "suites"
    dest.mkdir()
    (dest / "test_coverage_demo.py").write_text(
        "def test_old_module() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    body = (
        "from pages import SmokePage\n\n"
        "def test_page_imports() -> None:\n"
        "    assert SmokePage().ping() == 'pong'\n"
    )
    fake = FakeProvider()
    fake.enqueue_tools(
        ToolCall(
            id="w1",
            name="write_file",
            arguments=json.dumps({"path": str(dest / "test_from_spec.py"), "content": body}),
        )
    )
    fake.enqueue(json.dumps({"verdict": "diagnosed", "cause": "unknown", "summary": "wrote"}))
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    task = run_generator(
        store,
        spec="Ping returns pong.\nexpect: green",
        dest=dest,
        router=_router(fake, store, "g-col"),
        project_root=tmp_path,
        run_id="g-col",
        gate_mode="collect",
    )
    assert task.gate is not None
    assert task.gate["mode"] == "collect"
    assert task.gate["executed"] is True, task.gate
    assert task.gate["accepted"] is True
    assert task.gate.get("mock_driver") is False
    nodeid = str(task.gate["nodeid"])
    assert "test_coverage_demo" not in nodeid
    user = fake.requests[0].messages[0].content
    assert "HAS_PAGES: yes" in user
    assert "questline_ctx is a pytest fixture, not a module" in user
    assert "SmokePage" in user
    assert "ping" in user
    assert "from questline_ctx import" in user  # the "Never write" example
    assert "Never write `from questline_ctx import" in user
    assert "Do not pytest.skip when listed Page hooks can implement the spec." in user
    write_to = next(
        ln.split(":", 1)[1].strip()
        for ln in user.splitlines()
        if ln.startswith("WRITE_TEST_TO:")
    )
    assert write_to.startswith("suites/")
    assert ":" not in Path(write_to).name
    assert fake.requests[0].max_tokens >= 2048
    store.close()


def test_authoring_hints_marks_deferred_and_locators(tmp_path: Path) -> None:
    from questline.ai.agents.generator import _authoring_hints

    pages = tmp_path / "pages"
    pages.mkdir()
    (pages / "__init__.py").write_text(
        "class HudPage:\n"
        "    def get_amber(self) -> int:\n"
        '        """Hook GetAmber."""\n'
        "        return 0\n"
        "    def ensure_in_combat(self, level_index: int = 0) -> None:\n"
        '        """LoadLevel; combat session active."""\n'
        "        return None\n"
        "    def tap_ui(self) -> None:\n"
        '        """Deferred: would tap until Poco."""\n'
        "        raise RuntimeError('no')\n",
        encoding="utf-8",
    )
    (tmp_path / "locators.yaml").write_text(
        "pages:\n  Hud:\n    pause:\n      by: name\n      value: Btn\n",
        encoding="utf-8",
    )
    text = _authoring_hints(tmp_path)
    assert "HOOKS_FIRST" in text
    assert "Do not pytest.skip" in text
    assert "get_amber()" in text
    assert "ensure_in_combat(level_index)" in text
    assert "tap_ui() (deferred" in text
    assert "Hud: pause" in text
    assert "expect(page.get_amber()).equals(50).evaluate()" in text
    assert "Never expect(x).to_equal" in text


def test_generator_does_not_gate_existing_suite_file(tmp_path: Path) -> None:
    dest = tmp_path / "suites"
    dest.mkdir()
    (dest / "test_coverage_demo.py").write_text(
        "def test_old_module() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    fake = FakeProvider()
    fake.enqueue(
        json.dumps({"verdict": "passed", "cause": "unknown", "summary": "no write"})
    )
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    task = run_generator(
        store,
        spec="Tap Siguiente Nivel.\nexpect: green",
        dest=dest,
        router=_router(fake, store, "g-old"),
        project_root=tmp_path,
        run_id="g-old",
        gate_mode="collect",
        task_id="gen-no-write",
    )
    assert task.gate is not None
    assert task.gate["accepted"] is False
    assert task.gate["executed"] is False
    assert "test_coverage_demo" not in str(task.gate.get("nodeid") or "")
    store.close()


def test_generator_salvages_markdown_pytest(tmp_path: Path) -> None:
    dest = tmp_path / "suites"
    dest.mkdir()
    (dest / "test_coverage_demo.py").write_text(
        "def test_old_module() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    body = "def test_from_spec() -> None:\n    assert True\n"
    fake = FakeProvider()
    fake.enqueue(
        json.dumps(
            {
                "verdict": "diagnosed",
                "cause": "unknown",
                "summary": f"proposed test\n```python\n{body}```",
            }
        )
    )
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    task = run_generator(
        store,
        spec="Ping returns pong.\nexpect: green",
        dest=dest,
        router=_router(fake, store, "g-salv"),
        project_root=tmp_path,
        run_id="g-salv",
        gate_mode="collect",
        task_id="gen-salvage1",
    )
    assert task.gate is not None
    assert task.gate["accepted"] is True, task.gate
    nodeid = str(task.gate["nodeid"])
    assert nodeid.endswith("test_gen_salvage1.py")
    assert "test_coverage_demo" not in nodeid
    written = (tmp_path / nodeid).read_text(encoding="utf-8")
    assert "def test_from_spec" in written
    store.close()


def test_generator_rate_limited_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("questline.ai.router._sleep_s", lambda s: None)
    dest = tmp_path / "suites"
    dest.mkdir()
    fake = FakeProvider(name="groq")
    fake.enqueue(RateLimitedError("HTTP 429 from https://api.groq.com/openai/v1/chat/completions"))
    fake.enqueue(RateLimitedError("HTTP 429 from https://api.groq.com/openai/v1/chat/completions"))
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    task = run_generator(
        store,
        spec="When the player taps Siguiente Nivel: 1, combat loads.\nexpect: green",
        dest=dest,
        router=_router(fake, store, "g-429"),
        project_root=tmp_path,
        run_id="g-429",
        gate_mode="collect",
        task_id="gen-rate1",
    )
    assert task.gate is not None
    assert task.gate["reason"] == "rate_limited"
    assert task.gate["accepted"] is False
    assert task.verdict == "inconclusive"
    assert "no pytest file written" not in (task.summary or "")
    assert "429" in (task.summary or "")
    store.close()


def test_generator_rebuild_includes_history(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db")
    store.save_agent_task(
        task_id="gen-old",
        kind="generate",
        run_id=None,
        test_id="t-rebuild",
        status="ok",
        verdict="inconclusive",
        cause="flaky",
        prompt_version="v1",
        artifact_path="x",
        created_at="2026-09-20T00:00:00+00:00",
    )
    fake = FakeProvider()
    fake.enqueue(json.dumps({"verdict": "inconclusive", "cause": "flaky", "summary": "need spec"}))
    dest = tmp_path / "out"
    dest.mkdir()
    task = run_generator(
        store,
        spec="expect: green\nRebuild this flaky test.",
        dest=dest,
        router=_router(fake, store, "g3"),
        project_root=tmp_path,
        rebuild_test_id="t-rebuild",
        run_id="g3",
    )
    assert fake.requests
    user = fake.requests[0].messages[0].content
    assert "inconclusive" in user or "t-rebuild" in user
    assert task.kind == "generate"
    store.close()


class _UnitGenProvider(FakeProvider):
    def complete(self, req):  # type: ignore[no-untyped-def]
        self.last_request = req
        self.requests.append(req)
        text = req.messages[0].content if req.messages else ""
        if "TOOL RESULTS" not in text:
            line = next(ln for ln in text.splitlines() if ln.startswith("WRITE_TEST_TO:"))
            path = line.split(":", 1)[1].strip()
            body = (
                "from questline.core.errors import QuestlineError\n\n"
                "def test_questline_error_message() -> None:\n"
                "    assert str(QuestlineError('x')) == 'x'\n"
            )
            return LlmResponse(
                text="",
                tool_calls=(
                    ToolCall(
                        id="w1",
                        name="write_file",
                        arguments=json.dumps({"path": path, "content": body}),
                    ),
                ),
                usage=self.usage,
                provider=self.name,
                model=self.model,
                duration_ms=1.0,
            )
        return LlmResponse(
            text=json.dumps(
                {"verdict": "passed", "cause": "unknown", "summary": "patch ready"}
            ),
            usage=self.usage,
            provider=self.name,
            model=self.model,
            duration_ms=1.0,
        )


def test_unit_gen_patch_never_auto_commits(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "store.db", artifacts_dir=tmp_path / "arts")
    rec = _UnitGenProvider()

    def run_pytest(_nodeid: str) -> dict:
        return {"returncode": 0, "green": True, "stdout": "1 passed", "stderr": ""}

    task = run_unit_gen(
        store,
        module_path="questline.core.errors",
        router=_router(rec, store, "ug1"),
        project_root=tmp_path,
        run_pytest=run_pytest,
        gate_run=run_pytest,
    )
    assert task.gate is not None
    assert task.gate["auto_commit"] is False
    assert task.gate["executed"] is True
    assert task.patch
    assert Path(task.patch).is_file()
    assert "--- /dev/null" in Path(task.patch).read_text(encoding="utf-8")
    store.close()
