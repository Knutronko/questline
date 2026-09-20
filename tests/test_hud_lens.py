"""HUD GameLens + telemetry + balance-agent API (FP-G4)."""

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
    token = res.json()["csrf_token"]
    assert res.cookies.get(CSRF_COOKIE) == token
    return token


def test_list_snapshots_and_typed_diff(client: TestClient) -> None:
    snaps = client.get("/api/lens/snapshots")
    assert snaps.status_code == 200
    body = snaps.json()
    assert body["empty"] is False
    ids = {s["id"] for s in body["snapshots"]}
    assert "1.0.0" in ids and "1.1.0" in ids
    for row in body["snapshots"]:
        assert "artifact_path" not in row
        art = row.get("artifact") or ""
        assert "Users" not in art
        assert ":\\" not in art and "/home/" not in art

    diff = client.get("/api/lens/diff", params={"a": "1.0.0", "b": "1.1.0"})
    assert diff.status_code == 200
    payload = diff.json()
    kinds = {e["kind"] for e in payload["diff"]["entries"]}
    assert "added_entity" in kinds
    impl = payload["implications"]
    assert impl is not None
    gap_text = " ".join(impl.get("gaps") or [])
    assert "combat.damage" in gap_text
    assert "snap-unset" in gap_text


def test_telemetry_sessions_label_lose_and_unset(client: TestClient) -> None:
    res = client.get("/api/telemetry/sessions")
    assert res.status_code == 200
    sessions = {s["id"]: s for s in res.json()["sessions"]}
    unset = sessions["sess-unset"]
    assert unset["outcome"] == "lose"
    assert any("measured play" in n for n in unset["notes"])
    assert any("snap-unset" in n for n in unset["notes"])
    detail = client.get("/api/telemetry/sessions/sess-unset")
    assert detail.status_code == 200
    assert detail.json()["session"]["summary"]["leak_count"] == 3


def test_agent_run_fake_llm_persists(client: TestClient) -> None:
    token = _csrf(client)
    res = client.post(
        "/api/lens/agent/run",
        json={
            "snapshot_a": "1.0.0",
            "snapshot_b": "1.1.0",
            "question": "What should I retune?",
            "profile": "mock",
        },
        headers={CSRF_HEADER: token},
    )
    assert res.status_code == 200, res.text
    turn = res.json()["turn"]
    assert turn["status"] == "ok"
    assert turn["framing"] == "model reasoning"
    assert turn["priorities"]
    gap_text = " ".join(turn["gaps"])
    assert "combat.damage" in gap_text
    assert "snap-unset" in gap_text
    measured = turn["citations"]["measured"]
    assert measured["session_count"] >= 1
    listed = client.get("/api/lens/agent/turns")
    assert listed.status_code == 200
    ids = {t["id"] for t in listed.json()["turns"]}
    assert turn["id"] in ids
    got = client.get(f"/api/lens/agent/turns/{turn['id']}")
    assert got.status_code == 200
    assert got.json()["turn"]["priorities"] == turn["priorities"]


def test_agent_run_requires_csrf(client: TestClient) -> None:
    res = client.post(
        "/api/lens/agent/run",
        json={"snapshot_a": "1.0.0", "snapshot_b": "1.1.0"},
    )
    assert res.status_code == 403


def test_agent_run_read_only_blocked(hud_store, tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")
    app = create_app(
        store=hud_store,
        read_only=True,
        project_root=tmp_path,
        config_path=cfg,
    )
    with TestClient(app) as c:
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/lens/agent/run",
            json={"snapshot_a": "1.0.0", "snapshot_b": "1.1.0"},
            headers={CSRF_HEADER: token},
        )
        assert res.status_code == 403
        snaps = c.get("/api/lens/snapshots")
        assert snaps.status_code == 200
        assert snaps.json()["empty"] is False


def test_lens_not_found_and_indexes(client: TestClient) -> None:
    assert client.get("/api/lens/snapshots/nope").status_code == 404
    assert client.get("/api/lens/diff", params={"a": "nope", "b": "1.1.0"}).status_code == 404
    assert client.get("/api/lens/implications/missing").status_code == 404
    assert client.get("/api/telemetry/sessions/missing").status_code == 404
    assert client.get("/api/lens/agent/turns/missing").status_code == 404
    snap = client.get("/api/lens/snapshots/1.0.0")
    assert snap.status_code == 200
    assert snap.json()["snapshot"]["id"] == "1.0.0"
    impls = client.get("/api/lens/implications")
    assert impls.status_code == 200
    assert impls.json()["empty"] is False
    pair = impls.json()["implications"][0]["id"]
    detail = client.get(f"/api/lens/implications/{pair}")
    assert detail.status_code == 200
    assert "combat.damage" in " ".join(detail.json()["implications"].get("gaps") or [])


def test_agent_skipped_when_no_llm(hud_store, tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")
    app = create_app(
        store=hud_store,
        project_root=tmp_path,
        config_path=cfg,
    )
    with TestClient(app) as c:
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/lens/agent/run",
            json={"snapshot_a": "1.0.0", "snapshot_b": "1.1.0", "profile": "mock"},
            headers={CSRF_HEADER: token},
        )
        assert res.status_code == 200
        turn = res.json()["turn"]
        assert turn["status"] == "skipped"
        assert turn["pending"] == "no-provider"
        assert any("combat.damage" in g for g in turn["gaps"])


def test_agent_run_fake_kind_via_profile(hud_store, tmp_path: Path) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text(
        "\n".join(
            [
                "[profile.ai_fake]",
                'driver = "mock"',
                'ai.candidates = ["fake"]',
                "ai.budget_per_call_usd = 10.0",
                "ai.budget_per_run_usd = 10.0",
                "[profile.ai_fake.ai.providers.fake]",
                'kind = "fake"',
                'model = "fake-test"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    app = create_app(
        store=hud_store,
        project_root=tmp_path,
        config_path=cfg,
    )
    with TestClient(app) as c:
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/lens/agent/run",
            json={
                "snapshot_a": "1.0.0",
                "snapshot_b": "1.1.0",
                "profile": "ai_fake",
            },
            headers={CSRF_HEADER: token},
        )
        assert res.status_code == 200, res.text
        turn = res.json()["turn"]
        assert turn["status"] == "ok"
        assert any("combat.damage" in g for g in turn["gaps"])
