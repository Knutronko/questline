"""HUD Unity chip API: allow-listed status, CSRF, read-only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from questline.core.events import EventBus
from questline.hud.fixtures import seed_fixture_store
from questline.hud.security import CSRF_COOKIE, CSRF_HEADER
from questline.hud.server import create_app
from questline.unity_cli.client import UnityRun
from questline.unity_cli.status import PUBLIC_KEYS

_SECRET = "sekret-token"


class Script:
    def __init__(self, mapping: dict[tuple[str, ...], UnityRun]) -> None:
        self.calls: list[list[str]] = []
        self.mapping = mapping

    def __call__(
        self, args: list[str], _timeout: float, _env: dict[str, str]
    ) -> UnityRun:
        self.calls.append(list(args))
        for key, run in self.mapping.items():
            if tuple(args[: len(key)]) == key:
                return run
        return UnityRun(returncode=1, stdout="", stderr="", timed_out=False)


@pytest.fixture()
def client(tmp_path: Path):
    root = tmp_path / "proj"
    root.mkdir()
    project = root / "DemoGame"
    (root / "questline.toml").write_text(
        '[profile.editor]\ndriver = "questline"\ntarget_platform = "editor"\n'
        "[profile.editor.unity_cli]\nensure_editor = false\n"
        f'project = "{project.as_posix()}"\n',
        encoding="utf-8",
    )
    store = seed_fixture_store(root / ".questline" / "store.db")
    script = Script(
        {
            ("--version",): UnityRun(returncode=0, stdout="1.2.3-beta.1\n", stderr=""),
            ("editors", "running"): UnityRun(
                returncode=0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "evalToken": _SECRET,
                        "data": [
                            {
                                "projectPath": str(project),
                                "isPlaying": False,
                                "evalToken": _SECRET,
                            }
                        ],
                    }
                ),
                stderr=f"evalToken={_SECRET}",
            ),
            ("status",): UnityRun(
                returncode=0,
                stdout=json.dumps({"success": True, "data": {"state": "ready"}}),
                stderr="",
            ),
            ("open",): UnityRun(returncode=0, stdout="{}", stderr=""),
            ("command", "editor_play"): UnityRun(returncode=0, stdout="{}", stderr=""),
        }
    )
    app = create_app(
        store=store,
        bus=EventBus(),
        project_root=root,
        config_path=root / "questline.toml",
    )
    app.state.unity_which = lambda _name: "unity"
    app.state.unity_runner = script

    def _wait(**_kwargs: object) -> None:
        return None

    app.state.unity_wait = _wait
    with TestClient(app) as c:
        c.script = script  # type: ignore[attr-defined]
        yield c
    store.close()


def _csrf(client: TestClient) -> str:
    res = client.get("/api/csrf")
    assert res.status_code == 200
    token = res.json()["csrf_token"]
    assert res.cookies.get(CSRF_COOKIE) == token
    return token


def _assert_clean(payload: dict[str, Any]) -> None:
    blob = json.dumps(payload)
    assert _SECRET not in blob
    assert "evalToken" not in blob
    assert "Users" not in blob
    assert "DemoGame" in blob
    assert ":\\" not in blob
    assert "/Users/" not in blob


def test_status_allow_list(client: TestClient) -> None:
    res = client.get("/api/unity/status", params={"profile": "editor"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert set(body["unity"]) == PUBLIC_KEYS
    assert body["unity"]["available"] is True
    assert body["unity"]["cli_version"] == "1.2.3-beta.1"
    assert body["unity"]["editor_running"] is True
    assert body["unity"]["play_mode"] is False
    assert body["unity"]["pipeline"] == "yes"
    assert body["unity"]["project_name"] == "DemoGame"
    _assert_clean(body)
    meta = client.get("/api/meta")
    assert meta.json()["api"]["unity"] is True
    assert meta.json()["api"]["revision"] == 10


def test_ensure_requires_csrf_and_matches_cli(client: TestClient) -> None:
    bare = client.post("/api/unity/ensure-editor", json={"profile": "editor"})
    assert bare.status_code == 403
    token = _csrf(client)
    res = client.post(
        "/api/unity/ensure-editor",
        json={"profile": "editor"},
        headers={CSRF_HEADER: token},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["wire_ready"] is True
    assert body["unity"]["project_name"] == "DemoGame"
    _assert_clean(body)
    ops = [call[0] for call in client.script.calls]  # type: ignore[attr-defined]
    assert "open" not in ops or "command" in ops


def test_ensure_outside_config_forbidden(client: TestClient) -> None:
    token = _csrf(client)
    res = client.post(
        "/api/unity/ensure-editor",
        json={"profile": "editor", "config": "../questline.toml"},
        headers={CSRF_HEADER: token},
    )
    assert res.status_code in {403, 404}


def test_read_only_blocks_ensure(tmp_path: Path) -> None:
    root = tmp_path / "proj"
    root.mkdir()
    (root / "questline.toml").write_text(
        '[profile.mock]\ndriver = "mock"\n',
        encoding="utf-8",
    )
    store = seed_fixture_store(root / ".questline" / "store.db")
    app = create_app(
        store=store,
        project_root=root,
        config_path=root / "questline.toml",
        read_only=True,
    )
    app.state.unity_which = lambda _name: None
    with TestClient(app) as c:
        status = c.get("/api/unity/status", params={"profile": "mock"})
        assert status.status_code == 200
        assert status.json()["unity"]["available"] is False
        token = c.get("/api/csrf").json()["csrf_token"]
        res = c.post(
            "/api/unity/ensure-editor",
            json={"profile": "mock"},
            headers={CSRF_HEADER: token},
        )
        assert res.status_code == 403
    store.close()
