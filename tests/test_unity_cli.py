"""Unity CLI sidecar: feature-detect, ensure-editor, Wire wait, doctor allow-list."""

from __future__ import annotations

import json
import socket
import sys
import threading
from pathlib import Path

import pytest
from typer.testing import CliRunner

from questline.cli import app
from questline.core.config import load_settings
from questline.core.errors import AuthoringError, InfraError
from questline.unity_cli.client import UnityCli, UnityRun, parse_cli_stdout
from questline.unity_cli.ensure import EnsureResult, ensure_editor, maybe_ensure_editor
from questline.unity_cli.status import PUBLIC_KEYS, UnityStatus, probe_status
from questline.unity_cli.wire_wait import wait_for_editor_wire

runner = CliRunner()
_SECRET = "sekret-token"


class Script:
    def __init__(self, mapping: dict[tuple[str, ...], UnityRun]) -> None:
        self.calls: list[list[str]] = []
        self.envs: list[dict[str, str]] = []
        self.mapping = mapping

    def __call__(
        self, args: list[str], timeout_s: float, extra_env: dict[str, str]
    ) -> UnityRun:
        self.calls.append(list(args))
        self.envs.append(dict(extra_env))
        for key, run in self.mapping.items():
            if tuple(args[: len(key)]) == key:
                return run
        return UnityRun(returncode=1, stdout="", stderr="", timed_out=False)


def _ops(calls: list[list[str]]) -> list[str]:
    out: list[str] = []
    for args in calls:
        if args[:1] == ["--version"]:
            out.append("version")
        elif args[:2] == ["editors", "running"]:
            out.append("editors")
        elif args[:1] == ["open"]:
            out.append("open")
        elif args[:2] == ["command", "editor_play"]:
            out.append("play")
        elif args[:2] == ["command", "editor_status"]:
            out.append("editor_status")
        elif args[:1] == ["status"]:
            out.append("status")
        else:
            out.append("other")
    return out


def _cli(script: Script) -> UnityCli:
    return UnityCli(which=lambda _name: "unity", runner=script)


def _settings(tmp_path: Path, *, project: str | None = None, ensure: bool = False) -> object:
    lines = [
        "[profile.editor]",
        'driver = "questline"',
        'target_platform = "editor"',
        'target_host = "127.0.0.1"',
        "target_port = 13000",
        "wait.interval = 0.05",
        "wait.deadline = 1",
        "wait.probe = 0.05",
    ]
    if project is not None or ensure:
        lines.append("[profile.editor.unity_cli]")
        lines.append(f"ensure_editor = {'true' if ensure else 'false'}")
        lines.append("command_timeout_s = 5")
        lines.append("wire_timeout_s = 1")
        lines.append("probe_timeout_s = 1")
        if project is not None:
            safe = Path(project).as_posix()
            lines.append(f'project = "{safe}"')
    path = tmp_path / "questline.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return load_settings(
        config_path=path, profile="editor", project_root=tmp_path, environ={}
    )


def _version() -> UnityRun:
    return UnityRun(returncode=0, stdout="1.2.3-beta.1\n", stderr="")


def _editors(project: str, *, playing: bool | None) -> UnityRun:
    row: dict[str, object] = {
        "projectPath": project,
        "evalToken": _SECRET,
    }
    if playing is not None:
        row["isPlaying"] = playing
    body = {
        "success": True,
        "command": "editors running",
        "evalToken": _SECRET,
        "data": [row],
    }
    return UnityRun(returncode=0, stdout=json.dumps(body), stderr=f"evalToken={_SECRET}")


def _empty_editors() -> UnityRun:
    return UnityRun(
        returncode=0,
        stdout=json.dumps({"success": True, "data": []}),
        stderr="",
    )


def _ready() -> UnityRun:
    return UnityRun(
        returncode=0,
        stdout=json.dumps({"success": True, "data": {"state": "ready"}}),
        stderr="",
    )


def _assert_public(payload: dict) -> None:
    blob = json.dumps(payload)
    assert _SECRET not in blob
    assert "evalToken" not in blob
    assert "Users" not in blob
    assert ":\\Users" not in blob
    assert "/Users/" not in blob


def test_missing_cli_is_a_warning_not_a_crash(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    cli = UnityCli(which=lambda _name: None)
    status = probe_status(settings, cli=cli)
    assert status.available is False
    assert status.pipeline == "unknown"
    public = status.to_public()
    assert set(public) == PUBLIC_KEYS
    _assert_public(public)
    result = ensure_editor(settings, cli=cli)
    assert result.skipped is True
    assert result.ok is False
    assert result.wire_ready is False
    _assert_public(result.to_public())


def test_running_and_playing_skips_open(tmp_path: Path) -> None:
    project = str(tmp_path / "DemoGame")
    settings = _settings(tmp_path, project=project)
    script = Script(
        {
            ("--version",): _version(),
            ("editors", "running"): _editors(project, playing=True),
            ("status",): _ready(),
        }
    )
    waited: dict[str, object] = {}

    def _wait(**kwargs: object) -> None:
        waited.update(kwargs)

    result = ensure_editor(settings, cli=_cli(script), wait_wire=_wait)
    assert result.ok is True
    assert result.wire_ready is True
    assert "open" not in _ops(script.calls)
    assert "play" not in _ops(script.calls)
    assert waited["host"] == "127.0.0.1"
    assert waited["port"] == 13000
    public = result.to_public()
    assert public["unity"]["play_mode"] is True
    assert public["unity"]["project_name"] == "DemoGame"
    assert public["unity"]["pipeline"] == "yes"
    assert public["unity"]["cli_version"] == "1.2.3-beta.1"
    _assert_public(public)
    assert project not in json.dumps(public)
    assert all("--json" in call for call in script.calls)


def test_ensure_opens_then_plays_then_waits(tmp_path: Path) -> None:
    project = str(tmp_path / "DemoGame")
    settings = _settings(tmp_path, project=project)
    script = Script(
        {
            ("--version",): _version(),
            ("editors", "running"): _empty_editors(),
            ("open",): UnityRun(returncode=0, stdout="{}", stderr=""),
            ("command", "editor_play"): UnityRun(returncode=0, stdout="{}", stderr=""),
        }
    )

    def _wait(**_kwargs: object) -> None:
        return None

    result = ensure_editor(settings, cli=_cli(script), wait_wire=_wait)
    assert result.ok is True
    ops = _ops(script.calls)
    assert "open" in ops
    assert "play" in ops
    assert ops.index("open") < ops.index("play")
    assert Path(script.envs[ops.index("open")]["UNITY_PROJECT_PATH"]) == Path(project)
    assert project not in json.dumps(result.to_public())


def test_open_interrupt_and_timeout(tmp_path: Path) -> None:
    project = str(tmp_path / "DemoGame")
    settings = _settings(tmp_path, project=project)
    base = {
        ("--version",): _version(),
        ("editors", "running"): _empty_editors(),
    }
    interrupted = Script(
        {
            **base,
            ("open",): UnityRun(returncode=130, stdout="", stderr=f"evalToken={_SECRET}"),
        }
    )
    result = ensure_editor(settings, cli=_cli(interrupted))
    assert result.ok is False
    assert result.skipped is False
    assert "exit 130" in result.detail
    assert _SECRET not in result.detail
    _assert_public(result.to_public())

    timed = Script(
        {
            **base,
            ("open",): UnityRun(returncode=None, stdout="", stderr="", timed_out=True),
        }
    )
    timeout = ensure_editor(settings, cli=_cli(timed))
    assert timeout.ok is False
    assert "timed out" in timeout.detail


def test_unset_project_skips_without_open(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    script = Script(
        {
            ("--version",): _version(),
            ("editors", "running"): _empty_editors(),
        }
    )
    result = ensure_editor(settings, cli=_cli(script))
    assert result.skipped is True
    assert "open" not in _ops(script.calls)
    assert "project is unset" in result.detail


def test_editor_status_when_play_mode_missing(tmp_path: Path) -> None:
    project = str(tmp_path / "DemoGame")
    settings = _settings(tmp_path, project=project)
    script = Script(
        {
            ("--version",): _version(),
            ("editors", "running"): _editors(project, playing=None),
            ("status",): _ready(),
            ("command", "editor_status"): UnityRun(
                returncode=0,
                stdout=json.dumps({"success": True, "data": {"isPlaying": False}}),
                stderr="",
            ),
        }
    )
    status = probe_status(settings, cli=_cli(script))
    assert "editor_status" in _ops(script.calls)
    assert status.play_mode is False
    assert status.editor_running is True
    assert status.project_open is True


def test_probe_timeout(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    script = Script(
        {
            ("--version",): UnityRun(returncode=None, stdout="", stderr="", timed_out=True),
        }
    )
    status = probe_status(settings, cli=_cli(script))
    assert status.available is True
    assert "timed out" in status.detail
    assert _ops(script.calls) == ["version"]


def test_parse_json_after_banner() -> None:
    payload = parse_cli_stdout('Unity CLI\n{"success": true, "data": {"version": "9.9.9"}}')
    assert isinstance(payload, dict)
    assert payload["data"]["version"] == "9.9.9"


def test_subprocess_exit_codes_and_timeout() -> None:
    cli = UnityCli(binary=sys.executable, which=lambda _name: sys.executable)
    ok = cli.run(["-c", "print('9.9.9')"], timeout_s=5)
    assert ok.returncode == 0
    assert "9.9.9" in ok.stdout
    interrupted = cli.run(["-c", "import sys; sys.exit(130)"], timeout_s=5)
    assert interrupted.returncode == 130
    timed = cli.run(["-c", "import time; time.sleep(5)"], timeout_s=0.2)
    assert timed.timed_out is True
    missing = UnityCli(which=lambda _name: None)
    assert missing.available() is False
    assert missing.run(["--version"], timeout_s=1).missing is True


def test_wire_hello_success_and_fail() -> None:
    port = _serve_hello({"ok": True, "result": {"protocol_version": 2}})
    wait_for_editor_wire(host="127.0.0.1", port=port, timeout_s=2, interval_s=0.05)

    closed = _free_port()
    with pytest.raises(InfraError, match="hello"):
        wait_for_editor_wire(host="127.0.0.1", port=closed, timeout_s=0.35, interval_s=0.05)

    refused = _serve_hello({"ok": False, "error": "no"})
    with pytest.raises(InfraError, match="hello"):
        wait_for_editor_wire(host="127.0.0.1", port=refused, timeout_s=0.4, interval_s=0.05)


def test_wire_failure_on_ensure(tmp_path: Path) -> None:
    project = str(tmp_path / "DemoGame")
    settings = _settings(tmp_path, project=project)
    script = Script(
        {
            ("--version",): _version(),
            ("editors", "running"): _empty_editors(),
            ("open",): UnityRun(returncode=0, stdout="{}", stderr=""),
            ("command", "editor_play"): UnityRun(returncode=0, stdout="{}", stderr=""),
        }
    )

    def _wait(**_kwargs: object) -> None:
        raise InfraError("QuestlineWire did not answer hello on 127.0.0.1:13000 within 1s")

    result = ensure_editor(settings, cli=_cli(script), wait_wire=_wait)
    assert result.ok is False
    assert result.wire_ready is False
    assert "hello" in result.detail


def test_maybe_ensure_gates(tmp_path: Path) -> None:
    settings = _settings(tmp_path, ensure=False)
    assert maybe_ensure_editor(settings) is None

    android = load_settings(
        config_path=_write(
            tmp_path / "android.toml",
            '[profile.android_local]\ndriver = "questline"\n'
            'device = "adb"\ntarget_platform = "android"\n'
            "[profile.android_local.unity_cli]\nensure_editor = true\n",
        ),
        profile="android_local",
        project_root=tmp_path,
        environ={},
    )
    called: list[str] = []

    def _boom(_settings: object) -> EnsureResult:
        called.append("called")
        raise AssertionError("android must not ensure")

    assert maybe_ensure_editor(android, ensure=_boom) is None  # type: ignore[arg-type]
    assert called == []

    editor = _settings(tmp_path, project=str(tmp_path / "DemoGame"), ensure=True)

    def _skip(_settings: object) -> EnsureResult:
        return EnsureResult(
            ok=False,
            skipped=True,
            wire_ready=False,
            detail="unity CLI is not on PATH.",
            unity=UnityStatus(available=False),
        )

    skipped = maybe_ensure_editor(editor, ensure=_skip)  # type: ignore[arg-type]
    assert skipped is not None and skipped.skipped is True

    def _fail(_settings: object) -> EnsureResult:
        return EnsureResult(
            ok=False,
            skipped=False,
            wire_ready=False,
            detail="Wire hello failed.",
            unity=UnityStatus(available=True),
        )

    with pytest.raises(InfraError, match="Wire hello failed"):
        maybe_ensure_editor(editor, ensure=_fail)  # type: ignore[arg-type]


def test_config_table_env_and_secret(tmp_path: Path) -> None:
    bare = load_settings(project_root=tmp_path, environ={})
    assert bare.unity_cli.ensure_editor is False
    assert bare.unity_cli.project is None

    path = tmp_path / "questline.toml"
    path.write_text(
        '[profile.editor]\ndriver = "questline"\n'
        "[profile.editor.unity_cli]\nensure_editor = true\n"
        'project = "C:/Projects/DemoGame"\n',
        encoding="utf-8",
    )
    settings = load_settings(
        config_path=path,
        profile="editor",
        project_root=tmp_path,
        environ={"QUESTLINE_UNITY_CLI_ENSURE_EDITOR": "false"},
    )
    assert settings.unity_cli.ensure_editor is False
    assert settings.unity_cli.project_display_name() == "DemoGame"

    path.write_text(
        '[profile.editor]\nunity_cli = "nope"\n',
        encoding="utf-8",
    )
    with pytest.raises(AuthoringError, match="unity_cli"):
        load_settings(config_path=path, profile="editor", project_root=tmp_path, environ={})

    path.write_text(
        '[profile.editor]\n[profile.editor.unity_cli]\neval_token = "nope"\n',
        encoding="utf-8",
    )
    with pytest.raises(AuthoringError, match="Secret"):
        load_settings(config_path=path, profile="editor", project_root=tmp_path, environ={})


def test_doctor_and_cli_missing_is_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("questline.unity_cli.client.shutil.which", lambda _name: None)
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")
    result = runner.invoke(
        app,
        ["doctor", "--config", str(cfg), "--profile", "mock", "--no-ping"],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    assert "available=false" in result.stdout
    assert "wire-setup.md" in result.stdout
    status = runner.invoke(
        app, ["unity", "status", "--config", str(cfg), "--profile", "mock"]
    )
    assert status.exit_code == 0, status.stdout
    payload = json.loads(status.stdout)
    assert set(payload) == PUBLIC_KEYS
    assert payload["available"] is False
    _assert_public(payload)
    ensured = runner.invoke(
        app,
        ["unity", "ensure-editor", "--config", str(cfg), "--profile", "mock"],
    )
    assert ensured.exit_code == 0, ensured.stdout
    body = json.loads(ensured.stdout)
    assert body["skipped"] is True
    _assert_public(body)


def test_ensure_cli_failure_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = tmp_path / "questline.toml"
    cfg.write_text('[profile.mock]\ndriver = "mock"\n', encoding="utf-8")

    def _fail(_settings: object, **_kwargs: object) -> EnsureResult:
        return EnsureResult(
            ok=False,
            skipped=False,
            wire_ready=False,
            detail="Wire hello failed.",
            unity=UnityStatus(available=True, pipeline="no"),
        )

    monkeypatch.setattr("questline.unity_cli.ensure.ensure_editor", _fail)
    result = runner.invoke(
        app,
        ["unity", "ensure-editor", "--config", str(cfg), "--profile", "mock"],
    )
    assert result.exit_code == 1
    assert "Wire hello failed" in result.stdout
    assert _SECRET not in result.stdout


def test_probe_parses_alternate_shapes(tmp_path: Path) -> None:
    from questline.unity_cli.client import _text, parse_cli_stdout
    from questline.unity_cli.status import display_name, scrub_text

    assert scrub_text("  ") == ""
    assert scrub_text("evalToken=sekret") == "status withheld"
    assert display_name(None) is None
    assert display_name("..") is None
    assert display_name("evalToken") is None
    assert _text(None) == ""
    assert _text(b"ok") == "ok"
    assert parse_cli_stdout("") is None
    assert parse_cli_stdout("not json") is None

    project = tmp_path / "DemoGame"
    settings = _settings(tmp_path, project=str(project))
    withheld = UnityStatus(available=True, pipeline="bogus", detail="Bearer sekret")
    assert withheld.to_public()["pipeline"] == "unknown"
    assert withheld.to_public()["detail"] == "status withheld"

    missing_after = Script(
        {("--version",): UnityRun(returncode=None, stdout="", stderr="", missing=True)}
    )
    assert probe_status(settings, cli=_cli(missing_after)).available is False

    timed_editors = Script(
        {
            ("--version",): _version(),
            ("editors", "running"): UnityRun(
                returncode=None, stdout="", stderr="", timed_out=True
            ),
        }
    )
    assert "timed out" in probe_status(settings, cli=_cli(timed_editors)).detail

    for code, needle in ((130, "130"), (1, "failed")):
        failed = Script(
            {
                ("--version",): _version(),
                ("editors", "running"): UnityRun(returncode=code, stdout="", stderr=""),
            }
        )
        status = probe_status(settings, cli=_cli(failed))
        assert needle in status.detail
        assert status.editor_running is None

    wrapped = Script(
        {
            ("--version",): UnityRun(
                returncode=0,
                stdout=json.dumps({"success": True, "data": {"cliVersion": "4.0.0"}}),
                stderr="",
            ),
            ("editors", "running"): UnityRun(
                returncode=0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "data": {
                            "editors": [
                                "skip-me",
                                {"project": {"path": str(project)}, "playMode": "playing"},
                            ]
                        },
                    }
                ),
                stderr="",
            ),
            ("status",): UnityRun(
                returncode=0,
                stdout=json.dumps({"data": {"reachable": True}}),
                stderr="",
            ),
        }
    )
    playing = probe_status(settings, cli=_cli(wrapped))
    assert playing.cli_version == "4.0.0"
    assert playing.play_mode is True
    assert playing.pipeline == "yes"
    assert playing.project_name == "DemoGame"

    other = tmp_path / "OtherGame"
    different = Script(
        {
            ("--version",): UnityRun(
                returncode=0,
                stdout=json.dumps({"success": True, "data": "3.1.0"}),
                stderr="",
            ),
            ("editors", "running"): UnityRun(
                returncode=0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "data": {
                            "items": [
                                {"pid": 9, "project_path": str(other), "is_playing": "stopped"}
                            ]
                        },
                    }
                ),
                stderr="",
            ),
            ("status",): UnityRun(returncode=1, stdout="", stderr=""),
        }
    )
    # Configured project is DemoGame; a different folder is open.
    unmatched = probe_status(settings, cli=_cli(different))
    assert unmatched.cli_version == "3.1.0"
    assert unmatched.project_open is False
    assert unmatched.pipeline == "no"
    assert unmatched.project_name == "DemoGame"

    bare = _settings(tmp_path)
    first = Script(
        {
            ("--version",): UnityRun(returncode=0, stdout="not a version\n", stderr=""),
            ("editors", "running"): UnityRun(
                returncode=0,
                stdout=json.dumps(
                    {
                        "success": True,
                        "data": {
                            "running": [
                                {"processId": 3, "path": str(other), "playing": "no"}
                            ]
                        },
                    }
                ),
                stderr="",
            ),
            ("status",): UnityRun(
                returncode=0,
                stdout=json.dumps({"command": "status", "data": {"connection": "ready"}}),
                stderr="",
            ),
            ("command", "editor_status"): UnityRun(
                returncode=0,
                stdout=json.dumps({"data": {"editor": {"play_mode": "edit"}}}),
                stderr="",
            ),
        }
    )
    # playing "no" is already a flag, so editor_status is not required.
    named = probe_status(bare, cli=_cli(first))
    assert named.cli_version is None
    assert named.project_name == "OtherGame"
    assert named.play_mode is False
    assert named.pipeline == "yes"

    unknown_play = Script(
        {
            ("--version",): _version(),
            ("editors", "running"): UnityRun(
                returncode=0,
                stdout=json.dumps(
                    {"success": True, "data": {"pid": 1, "projectPath": str(other)}}
                ),
                stderr="",
            ),
            ("status",): UnityRun(returncode=130, stdout="", stderr=""),
        }
    )
    stalled = probe_status(bare, cli=_cli(unknown_play))
    assert stalled.pipeline == "unknown"
    assert stalled.play_mode is None


def test_ensure_play_failures_and_platform_gate(tmp_path: Path) -> None:
    project = str(tmp_path / "DemoGame")
    settings = _settings(tmp_path, project=project, ensure=True)
    base = {
        ("--version",): _version(),
        ("editors", "running"): _empty_editors(),
        ("open",): UnityRun(returncode=0, stdout="{}", stderr=""),
    }
    for play, needle in (
        (UnityRun(returncode=1, stdout="", stderr=""), "failed"),
        (UnityRun(returncode=130, stdout="", stderr=""), "130"),
        (UnityRun(returncode=None, stdout="", stderr="", missing=True), "not on PATH"),
        (UnityRun(returncode=None, stdout="", stderr="", timed_out=True), "timed out"),
    ):
        script = Script({**base, ("command", "editor_play"): play})
        result = ensure_editor(settings, cli=_cli(script))
        assert result.ok is False
        assert needle in result.detail

    mock = load_settings(
        config_path=_write(
            tmp_path / "mock.toml",
            '[profile.mock]\ndriver = "mock"\n'
            "[profile.mock.unity_cli]\nensure_editor = true\n",
        ),
        profile="mock",
        project_root=tmp_path,
        environ={},
    )
    def _should_not_run(_settings: object) -> None:
        raise AssertionError()

    assert maybe_ensure_editor(mock, ensure=_should_not_run) is None

    standalone = load_settings(
        config_path=_write(
            tmp_path / "stand.toml",
            '[profile.editor]\ndriver = "questline"\n'
            'target_platform = "standalone_exe"\n'
            "[profile.editor.unity_cli]\nensure_editor = true\n",
        ),
        profile="editor",
        project_root=tmp_path,
        environ={},
    )
    assert maybe_ensure_editor(standalone) is None


def test_subprocess_start_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import questline.unity_cli.client as client_mod

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("blocked")

    monkeypatch.setattr(client_mod.subprocess, "run", _boom)
    cli = UnityCli(binary=sys.executable, which=lambda _name: sys.executable)
    run = cli.run(["--version"], timeout_s=1)
    assert run.missing is True


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _serve_hello(payload: dict) -> int:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    srv.settimeout(2)
    port = int(srv.getsockname()[1])

    def _run() -> None:
        try:
            conn, _addr = srv.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(2)
            buf = b""
            while b"\n" not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                buf += chunk
            conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        srv.close()

    threading.Thread(target=_run, daemon=True).start()
    return port
