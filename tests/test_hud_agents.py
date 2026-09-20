"""HUD phase-12 agent buttons (triage / diagnose / heal)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from questline.core.events import EventBus
from questline.hud.fixtures import ScriptedBalanceProvider, seed_fixture_store
from questline.hud.security import CSRF_COOKIE
from questline.hud.server import create_app

CSRF_HEADER = "x-csrf-token"


@pytest.fixture()
def hud_store(tmp_path: Path):
    store = seed_fixture_store(tmp_path / "store.db")
    (tmp_path / "locators.yaml").write_text(
        "pages:\n  MainMenu:\n    play_button:\n      by: id\n      value: main.play\n",
        encoding="utf-8",
    )
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


def _mut(client: TestClient, path: str, payload: dict) -> object:
    token = _csrf(client)
    return client.post(path, json=payload, headers={CSRF_HEADER: token})


def test_triage_run_persists_clusters(client: TestClient) -> None:
    res = _mut(client, "/api/agents/triage", {"run_id": "run-a"})
    assert res.status_code == 200, res.text
    task = res.json()["task"]
    assert task["kind"] == "triage"
    assert task["verdict"] in {"diagnosed", "inconclusive"}
    assert task["clusters"]
    listed = client.get("/api/runs/run-a/agent-tasks")
    assert listed.status_code == 200
    assert listed.json()["empty"] is False


def test_diagnose_test(client: TestClient) -> None:
    res = _mut(
        client,
        "/api/agents/diagnose",
        {"run_id": "run-a", "test_id": "t-infra"},
    )
    assert res.status_code == 200, res.text
    task = res.json()["task"]
    assert task["kind"] == "diagnose"
    assert task["verdict"] == "diagnosed"


def test_heal_locator(client: TestClient) -> None:
    res = _mut(
        client,
        "/api/agents/heal",
        {"run_id": "run-a", "test_id": "t-locator"},
    )
    assert res.status_code == 200, res.text
    task = res.json()["task"]
    assert task["kind"] == "heal"
    sug = task.get("suggestion") or {}
    assert sug.get("writes") is False


def test_triage_requires_csrf(client: TestClient) -> None:
    res = client.post("/api/agents/triage", json={"run_id": "run-a"})
    assert res.status_code == 403


def test_agents_forbidden_in_read_only(hud_store, tmp_path: Path) -> None:
    app = create_app(
        store=hud_store,
        project_root=tmp_path,
        read_only=True,
    )
    with TestClient(app) as c:
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/agents/triage",
            json={"run_id": "run-a"},
            headers={CSRF_HEADER: token},
            cookies={CSRF_COOKIE: token},
        )
        assert res.status_code == 403
