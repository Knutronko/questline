"""HUD eval panel + generate endpoints."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from questline.core.events import EventBus
from questline.hud.fixtures import ScriptedBalanceProvider, seed_fixture_store
from questline.hud.server import create_app

CSRF_HEADER = "x-csrf-token"


@pytest.fixture()
def hud_store(tmp_path: Path):
    store = seed_fixture_store(tmp_path / "store.db")
    yield store
    store.close()


@pytest.fixture()
def client(hud_store, tmp_path: Path):
    bus = EventBus()
    hud_store.attach(bus)
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")
    app = create_app(
        store=hud_store,
        bus=bus,
        project_root=tmp_path,
        config_path=cfg,
    )
    app.state.llm_provider = ScriptedBalanceProvider()
    with TestClient(app) as c:
        yield c


def _csrf(client: TestClient) -> str:
    res = client.get("/api/csrf")
    assert res.status_code == 200
    return res.json()["csrf_token"]


def test_eval_list_and_compare(client: TestClient) -> None:
    listed = client.get("/api/eval/runs")
    assert listed.status_code == 200
    runs = listed.json()["runs"]
    ids = {r["id"] for r in runs}
    assert "eval-a" in ids
    assert "eval-b" in ids
    cmp = client.get("/api/eval/compare?a=eval-a&b=eval-b")
    assert cmp.status_code == 200
    delta = cmp.json()["compare"]["delta_b_minus_a"]
    assert "false_green_rate" in delta
    one = client.get("/api/eval/runs/eval-a")
    assert one.status_code == 200
    assert one.json()["run"]["cases"]


def test_eval_run_offline(client: TestClient) -> None:
    token = _csrf(client)
    res = client.post(
        "/api/eval/run",
        json={"agent": "maintainer", "provider": "fake"},
        headers={CSRF_HEADER: token},
    )
    assert res.status_code == 200, res.text
    run = res.json()["run"]
    assert run["case_count"] >= 10
    assert any(c.get("sabotage") and c.get("false_green") for c in run["cases"])


def test_generate_demo_writes_and_gates(client: TestClient, tmp_path: Path) -> None:
    token = _csrf(client)
    res = client.post(
        "/api/agents/generate",
        json={
            "spec": "When the player taps Play, HUD coins show 100.\nexpect: green",
            "dest": "generated-tests",
            "demo": True,
        },
        headers={CSRF_HEADER: token},
    )
    assert res.status_code == 200, res.text
    task = res.json()["task"]
    gate = task["gate"]
    assert gate["executed"] is True, gate
    assert gate["accepted"] is True
    listed = client.get("/api/agent-tasks?kind=generate")
    assert listed.status_code == 200
    ids = {t["id"] for t in listed.json()["tasks"]}
    assert task["id"] in ids
    nodeid = str(gate.get("nodeid") or "")
    assert "test_gen_" in nodeid
    assert (tmp_path / nodeid).is_file()
    assert gate.get("mode") == "execute"
    assert gate.get("mock_driver") is True


def test_generate_scripted_provider_without_demo_flag(
    client: TestClient, tmp_path: Path
) -> None:
    token = _csrf(client)
    res = client.post(
        "/api/agents/generate",
        json={
            "spec": "expect: green\nTap Play.",
            "dest": "from-scripted",
            "demo": False,
        },
        headers={CSRF_HEADER: token},
    )
    assert res.status_code == 200, res.text
    gate = res.json()["task"]["gate"]
    assert gate["executed"] is True, gate
    assert gate["accepted"] is True
    assert gate.get("mode") == "collect"
    assert gate.get("mock_driver") is True
    nodeid = str(gate.get("nodeid") or "")
    assert "test_gen_" in nodeid
    assert (tmp_path / nodeid).is_file()


def test_generate_collect_then_launcher_argv(client: TestClient, tmp_path: Path) -> None:
    token = _csrf(client)
    captured: dict[str, object] = {}

    class _Proc:
        pid = 77
        stdout = None

        def poll(self) -> int:
            return 0

        def wait(self) -> int:
            return 0

        def send_signal(self, _sig: int) -> None:
            return None

        def kill(self) -> None:
            return None

    def spawn(argv: list[str], **_k: object) -> _Proc:
        captured["argv"] = argv
        return _Proc()

    client.app.state.launcher._spawn = spawn  # type: ignore[attr-defined]
    (tmp_path / "suites").mkdir()
    (tmp_path / "suites" / "test_coverage_demo.py").write_text(
        "def test_old_module() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    gen = client.post(
        "/api/agents/generate",
        json={"spec": "expect: green\nPing.", "dest": "suites", "demo": False},
        headers={CSRF_HEADER: token},
    )
    assert gen.status_code == 200, gen.text
    gate = gen.json()["task"]["gate"]
    assert gate["mode"] == "collect"
    assert gate["accepted"] is True
    nodeid = gate["nodeid"]
    assert "test_coverage_demo" not in str(nodeid)
    assert "test_gen_" in str(nodeid)
    launched = client.post(
        "/api/launcher/start",
        json={
            "profile": "editor",
            "tests": [nodeid],
            "live_target": True,
            "config": "questline.toml",
        },
        headers={CSRF_HEADER: token},
    )
    assert launched.status_code == 200, launched.text
    argv = launched.json()["launcher"]["argv"]
    assert any(nodeid in str(part) for part in argv)


def test_generate_live_without_llm_is_400(
    hud_store, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.editor]\ndriver = "questline"\n', encoding="utf-8")
    app = create_app(
        store=hud_store,
        project_root=tmp_path,
        config_path=cfg,
    )
    with TestClient(app) as c:
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/agents/generate",
            json={"spec": "Ping returns pong.\nexpect: green", "demo": False},
            headers={CSRF_HEADER: token},
        )
        assert res.status_code == 400, res.text
        assert "GROQ_API_KEY" in res.json()["detail"]


def test_generate_demo_skips_suites_when_pages_exist(
    client: TestClient, tmp_path: Path
) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "suites").mkdir()
    token = _csrf(client)
    res = client.post(
        "/api/agents/generate",
        json={
            "spec": "When the player taps Play, HUD coins show 100.\nexpect: green",
            "dest": "suites",
            "demo": True,
        },
        headers={CSRF_HEADER: token},
    )
    assert res.status_code == 200, res.text
    assert not (tmp_path / "suites" / "test_from_spec.py").exists()
    gate = res.json()["task"]["gate"]
    nodeid = str(gate.get("nodeid") or "")
    assert "test_gen_" in nodeid
    assert (tmp_path / nodeid).is_file()
    assert not str(nodeid).startswith("suites/")
    assert gate.get("mock_driver") is True


def test_eval_read_only_blocks_run(hud_store, tmp_path: Path) -> None:
    app = create_app(
        store=hud_store,
        project_root=tmp_path,
        config_path=tmp_path / "questline.toml",
        read_only=True,
    )
    with TestClient(app) as c:
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/eval/run",
            json={"agent": "maintainer"},
            headers={CSRF_HEADER: token},
        )
        assert res.status_code == 403
