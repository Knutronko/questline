"""HUD REST + WebSocket integration tests against a fixture store."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from questline.core.events import EventBus, RunStarted, TestStarted
from questline.hud.fixtures import seed_fixture_store
from questline.hud.server import create_app


@pytest.fixture()
def hud_store(tmp_path: Path):
    store = seed_fixture_store(tmp_path / "store.db")
    yield store
    store.close()


@pytest.fixture()
def client(hud_store):
    bus = EventBus()
    hud_store.attach(bus)
    app = create_app(store=hud_store, bus=bus)
    with TestClient(app) as c:
        c.bus = bus  # type: ignore[attr-defined]
        yield c


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_runs_and_filters(client: TestClient) -> None:
    res = client.get("/api/runs")
    assert res.status_code == 200
    body = res.json()
    assert body["empty"] is False
    assert len(body["runs"]) == 2
    ids = {r["id"] for r in body["runs"]}
    assert ids == {"run-a", "run-b"}
    run_a = next(r for r in body["runs"] if r["id"] == "run-a")
    assert run_a["driver"] == "questline"
    assert run_a["device"] == "adb"
    assert run_a["infra_failures"] == 1
    assert run_a["passed"] == 1

    filtered = client.get("/api/runs", params={"profile": "editor"})
    assert len(filtered.json()["runs"]) == 1
    assert filtered.json()["runs"][0]["id"] == "run-b"


def test_run_detail_banner(client: TestClient) -> None:
    res = client.get("/api/runs/run-a")
    assert res.status_code == 200
    body = res.json()
    assert body["banner"]["infra_failures"] == 1
    assert body["banner"]["test_failures"] == 0
    assert len(body["tests"]) == 2


def test_test_detail_steps_death_artifacts(client: TestClient) -> None:
    res = client.get("/api/runs/run-a/tests/t-infra")
    assert res.status_code == 200
    body = res.json()
    assert body["test"]["verdict"] == "infra"
    assert body["steps"][0]["name"] == "open_shop"
    assert body["death_point"]["last_started_step"]["name"] == "open_shop"
    assert body["artifacts"]
    assert body["history"]  # includes run-a fail + run-b pass


def test_test_detail_nodeid_with_slashes(client: TestClient, hud_store) -> None:
    """Plugin uses pytest nodeid as test_id (paths with /) — API must accept it."""
    nid = "examples/wire-smoke/test_smoke.py::test_wire_v2_hierarchy_find_tap"
    bus = client.bus  # type: ignore[attr-defined]
    bus.publish(
        TestStarted(
            run_id="run-a",
            test_id=nid,
            nodeid=nid,
            timestamp=datetime.now(UTC),
        )
    )
    # Preferred: query param (safe for / and ::).
    res = client.get("/api/runs/run-a/test", params={"id": nid})
    assert res.status_code == 200, res.text
    assert res.json()["test"]["id"] == nid
    assert res.json()["test"]["nodeid"] == nid
    # Path form with {test_id:path} still works.
    res_path = client.get(f"/api/runs/run-a/tests/{nid}")
    assert res_path.status_code == 200, res_path.text
    assert res_path.json()["test"]["id"] == nid


def test_trends_flaky(client: TestClient) -> None:
    res = client.get("/api/trends")
    assert res.status_code == 200
    body = res.json()
    assert len(body["series"]) == 2
    flaky_ids = {f["nodeid"] for f in body["flaky_tests"]}
    assert "tests/demo.py::test_shop" in flaky_ids


def test_empty_store(tmp_path: Path) -> None:
    from questline.core.store import RunStore

    store = RunStore(tmp_path / "empty.db")
    app = create_app(store=store)
    with TestClient(app) as c:
        res = c.get("/api/runs")
        assert res.status_code == 200
        assert res.json()["empty"] is True
        assert res.json()["runs"] == []
    store.close()


def test_live_websocket_streams_events(client: TestClient) -> None:
    bus: EventBus = client.bus  # type: ignore[attr-defined]
    with client.websocket_connect("/live") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        bus.publish(
            RunStarted(
                run_id="live-1",
                profile="mock",
                timestamp=datetime(2026, 8, 11, tzinfo=UTC),
            )
        )
        bus.publish(
            TestStarted(
                run_id="live-1",
                test_id="lt1",
                nodeid="tests/x.py::test_y",
                timestamp=datetime(2026, 8, 11, 0, 0, 1, tzinfo=UTC),
            )
        )
        seen: list[str] = []
        for _ in range(8):
            msg = ws.receive_json()
            seen.append(str(msg.get("type")))
            if "RunStarted" in seen and "TestStarted" in seen:
                break
        assert "RunStarted" in seen
        assert "TestStarted" in seen
        ws.send_text("close")


def test_artifact_path_traversal_blocked(client: TestClient, tmp_path: Path) -> None:
    evil = tmp_path / "secret.txt"
    evil.write_text("nope", encoding="utf-8")
    res = client.get("/api/artifacts/file", params={"path": str(evil)})
    assert res.status_code == 403


def test_list_run_artifacts_and_file(client: TestClient, hud_store) -> None:
    res = client.get("/api/runs/run-a/artifacts")
    assert res.status_code == 200
    arts = res.json()["artifacts"]
    assert arts
    path = arts[0]["path"]
    file_res = client.get("/api/artifacts/file", params={"path": path})
    assert file_res.status_code == 200
    assert file_res.content == b"fakepng"

    missing = client.get("/api/runs/nope/artifacts")
    assert missing.status_code == 404

    gone = client.get(
        "/api/artifacts/file",
        params={"path": str(hud_store.artifacts_dir / "missing.bin")},
    )
    assert gone.status_code == 404


def test_run_and_test_not_found(client: TestClient) -> None:
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/runs/run-a/tests/missing").status_code == 404


def test_spa_fallback_and_asset(client: TestClient) -> None:
    res = client.get("/does-not-exist-route")
    assert res.status_code == 200
    # Hashed asset from Vite build (if present).
    index = client.get("/")
    assert index.status_code == 200


def test_missing_api_route_is_json_not_html(client: TestClient) -> None:
    res = client.get("/api/this-route-does-not-exist")
    assert res.status_code == 404
    assert "application/json" in res.headers.get("content-type", "")
    assert "<!DOCTYPE" not in res.text


def test_create_app_export(hud_store) -> None:
    from questline.hud import create_app as exported

    app = exported(store=hud_store)
    assert app.title == "Questline HUD"


def test_api_live_alias(client: TestClient) -> None:
    with client.websocket_connect("/api/live") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "hello"
        ws.send_text("close")
