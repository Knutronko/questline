"""HUD control-center API tests (launcher / quarantine / config / perf / CSRF)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from questline.core.events import EventBus
from questline.hud.fixtures import seed_fixture_store
from questline.hud.launcher import RunLauncher
from questline.hud.security import CSRF_COOKIE, CSRF_HEADER
from questline.hud.server import create_app


@pytest.fixture()
def hud_root(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "questline.toml").write_text(
        '[profile.mock]\ndriver = "mock"\nreporters = ["console"]\n'
        "wait.probe = 0.05\nwait.deadline = 0.5\nwait.interval = 0.01\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture()
def hud_store(hud_root: Path):
    store = seed_fixture_store(hud_root / ".questline" / "store.db")
    yield store
    store.close()


class _FakeProc:
    def __init__(self) -> None:
        self.pid = 4242
        self._code: int | None = None
        self._done = threading.Event()

    def poll(self) -> int | None:
        return self._code

    def wait(self) -> int:
        self._done.wait(timeout=30)
        return 0 if self._code is None else self._code

    def send_signal(self, _sig: int) -> None:
        self._code = -15
        self._done.set()

    def kill(self) -> None:
        self._code = -9
        self._done.set()


@pytest.fixture()
def client(hud_store, hud_root: Path):
    bus = EventBus()
    hud_store.attach(bus)
    fake = _FakeProc()

    def spawn(*_a: Any, **_k: Any) -> _FakeProc:
        return fake

    launcher = RunLauncher(
        project_root=hud_root,
        config_path=hud_root / "questline.toml",
        forward_url="http://127.0.0.1:8741/api/live/ingest",
        csrf_token="test-csrf",
        lock_dir=hud_root / ".questline" / "device-locks",
        spawn=spawn,  # type: ignore[arg-type]
    )
    app = create_app(
        store=hud_store,
        bus=bus,
        project_root=hud_root,
        config_path=hud_root / "questline.toml",
        quarantine_path=hud_root / "quarantine.yaml",
        launcher=launcher,
    )
    with TestClient(app) as c:
        c.bus = bus  # type: ignore[attr-defined]
        c.fake_proc = fake  # type: ignore[attr-defined]
        yield c


def _csrf(client: TestClient) -> str:
    res = client.get("/api/csrf")
    assert res.status_code == 200
    token = res.json()["csrf_token"]
    assert res.cookies.get(CSRF_COOKIE) == token
    return token


def _mut(client: TestClient, method: str, path: str, **kwargs: Any):
    token = _csrf(client)
    headers = kwargs.pop("headers", {})
    headers[CSRF_HEADER] = token
    return client.request(method, path, headers=headers, **kwargs)


def test_meta_and_csrf(client: TestClient) -> None:
    meta = client.get("/api/meta")
    assert meta.status_code == 200
    assert meta.json()["control_center"] is True
    assert meta.json()["read_only"] is False
    token = _csrf(client)
    assert token


def test_mutating_requires_csrf(client: TestClient) -> None:
    res = client.post("/api/launcher/start", json={"profile": "mock"})
    assert res.status_code == 403


def test_read_only_blocks_mutators(hud_store, hud_root: Path) -> None:
    app = create_app(
        store=hud_store,
        read_only=True,
        project_root=hud_root,
        config_path=hud_root / "questline.toml",
    )
    with TestClient(app) as c:
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/launcher/start",
            json={"profile": "mock"},
            headers={CSRF_HEADER: token},
        )
        assert res.status_code == 403
        assert "read-only" in res.json()["detail"].lower()


def test_launch_stop_mocked(client: TestClient) -> None:
    res = _mut(client, "POST", "/api/launcher/start", json={"profile": "mock", "tests": ["."]})
    assert res.status_code == 200, res.text
    body = res.json()["launcher"]
    assert body["state"] == "running"
    assert body["profile"] == "mock"
    assert "--questline-profile" in body["argv"]

    stop = _mut(client, "POST", "/api/launcher/stop")
    assert stop.status_code == 200
    st = client.get("/api/launcher").json()["launcher"]
    assert st["state"] in {"stopping", "finished", "error", "idle"}


def test_quarantine_add_remove_audit(client: TestClient, hud_root: Path) -> None:
    add = _mut(
        client,
        "POST",
        "/api/quarantine",
        json={
            "test_id": "tests/demo.py::test_flaky",
            "reason": "flake",
            "owner": "pablo",
            "exit_criteria": "3 greens",
        },
    )
    assert add.status_code == 200, add.text
    listed = client.get("/api/quarantine").json()
    assert any(e["test_id"] == "tests/demo.py::test_flaky" for e in listed["entries"])

    audit = _mut(
        client,
        "POST",
        "/api/quarantine/audit",
        json={"tests": [str(hud_root)], "rootdir": str(hud_root)},
    )
    assert audit.status_code == 200, audit.text
    assert audit.json()["ok"] is False  # ledger-only without marker

    rm = _mut(
        client,
        "DELETE",
        "/api/quarantine",
        params={"test_id": "tests/demo.py::test_flaky"},
    )
    assert rm.status_code == 200
    assert client.get("/api/quarantine").json()["entries"] == []


def test_profile_validate_rejects_invalid(client: TestClient) -> None:
    res = _mut(
        client,
        "POST",
        "/api/profiles/mock/validate",
        json={"fields": {"driver": "mock", "wait": {"probe": -1}}, "apply": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is False
    assert body["errors"]


def test_profile_diff_preview(client: TestClient) -> None:
    res = _mut(
        client,
        "POST",
        "/api/profiles/mock",
        json={
            "fields": {
                "driver": "mock",
                "reporters": ["console", "html"],
                "wait": {"probe": 0.05, "deadline": 0.5, "interval": 0.01},
            },
            "apply": False,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["ok"] is True
    assert "diff" in res.json()
    assert res.json()["saved"] is False


def test_perf_series_and_compare(client: TestClient) -> None:
    a = client.get("/api/perf/run-a")
    assert a.status_code == 200
    assert "fps" in a.json()["series"]
    assert a.json()["summary"]["fps"]["count"] == 4

    cmp_ = client.get("/api/perf/compare", params={"a": "run-a", "b": "run-b"})
    assert cmp_.status_code == 200
    deltas = {d["metric"]: d for d in cmp_.json()["deltas"]}
    assert "fps" in deltas
    assert deltas["fps"]["delta_avg"] is not None


def test_live_ingest_ok(client: TestClient) -> None:
    res = _mut(
        client,
        "POST",
        "/api/live/ingest",
        json={
            "type": "TestStarted",
            "run_id": "r1",
            "test_id": "t1",
            "nodeid": "x::y",
            "timestamp": "2026-08-11T12:00:00+00:00",
            "tags": {},
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "ok"

    bad = _mut(client, "POST", "/api/live/ingest", json={"run_id": "x"})
    assert bad.status_code == 400


def test_devices_endpoint(client: TestClient) -> None:
    res = client.get("/api/devices")
    assert res.status_code == 200
    assert "devices" in res.json()


def test_perf_correlation(client: TestClient) -> None:
    res = client.get("/api/perf/correlation")
    assert res.status_code == 200
    assert "tests" in res.json()
    # Fixture has flaky shop across run-a/run-b.
    nodeids = {t["nodeid"] for t in res.json()["tests"]}
    assert "tests/demo.py::test_shop" in nodeids


def test_profiles_list_and_get(client: TestClient) -> None:
    listed = client.get("/api/profiles")
    assert listed.status_code == 200
    assert "mock" in listed.json()["profiles"]
    got = client.get("/api/profiles/mock")
    assert got.status_code == 200
    assert got.json()["fields"]["driver"] == "mock"
    assert "QUESTLINE_API_KEY" in got.json()["secret_env_names"]
    missing = client.get("/api/profiles/nope")
    assert missing.status_code == 404


def test_profile_save_apply(client: TestClient, hud_root: Path) -> None:
    res = _mut(
        client,
        "POST",
        "/api/profiles/mock",
        json={
            "fields": {
                "driver": "mock",
                "reporters": ["console"],
                "wait": {"probe": 0.05, "deadline": 0.5, "interval": 0.01},
            },
            "apply": True,
        },
    )
    assert res.status_code == 200, res.text
    assert res.json()["saved"] is True
    text = (hud_root / "questline.toml").read_text(encoding="utf-8")
    assert "[profile.mock]" in text


def test_profile_rejects_secret_field(client: TestClient) -> None:
    res = _mut(
        client,
        "POST",
        "/api/profiles/mock/validate",
        json={"fields": {"driver": "mock", "api_key": "secret"}, "apply": False},
    )
    assert res.status_code == 200
    assert res.json()["ok"] is False


def test_reporters_and_concurrent_launch(client: TestClient) -> None:
    assert "console" in client.get("/api/reporters").json()["reporters"]
    first = _mut(client, "POST", "/api/launcher/start", json={"profile": "mock"})
    assert first.status_code == 200
    second = _mut(client, "POST", "/api/launcher/start", json={"profile": "mock"})
    assert second.status_code == 409
    _mut(client, "POST", "/api/launcher/stop")


def test_collect_tests_scoped(client: TestClient, hud_root: Path) -> None:
    res = client.get("/api/tests/collect", params={"path": str(hud_root)})
    assert res.status_code == 200
    assert "nodeids" in res.json()
