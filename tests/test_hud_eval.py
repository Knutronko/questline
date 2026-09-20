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
