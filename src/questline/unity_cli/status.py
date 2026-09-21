"""Allow-listed Unity CLI / Editor status. No tokens, no raw home paths."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from questline.core.config import Settings
from questline.unity_cli.client import UnityCli, UnityRun

PUBLIC_KEYS = frozenset(
    {
        "available",
        "cli_version",
        "pipeline",
        "editor_running",
        "play_mode",
        "project_name",
        "detail",
    }
)

_VERSION_RE = re.compile(r"^[0-9]+[0-9A-Za-z.+\-]*$")
_SENSITIVE = re.compile(
    r"(evalToken|eval_token|Bearer\s+\S+|[A-Za-z]:\\Users\\|\\Users\\|/Users/)",
    re.IGNORECASE,
)
_PLAY_KEYS = ("isPlaying", "is_playing", "playing", "playMode", "play_mode")
_PROJECT_KEYS = ("projectPath", "project_path", "path", "project")
_READY_STATES = frozenset({"ready", "connected", "running"})

_JSON_FLAGS = ("--json", "--non-interactive", "--no-banner")


def scrub_text(text: str) -> str:
    """Drop a detail string that would leak a token or a home path."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if _SENSITIVE.search(cleaned):
        return "status withheld"
    return cleaned[:500]


def display_name(path: str | None) -> str | None:
    """Last path segment only, when it is a project folder name."""
    if not path or not str(path).strip():
        return None
    name = Path(str(path).strip()).name
    if not name or name in {".", ".."} or any(sep in name for sep in ("/", "\\", ":")):
        return None
    if _SENSITIVE.search(name):
        return None
    return name


@dataclass
class UnityStatus:
    available: bool
    cli_version: str | None = None
    pipeline: str = "unknown"
    editor_running: bool | None = None
    play_mode: bool | None = None
    project_name: str | None = None
    detail: str = ""
    project_open: bool = False

    def to_public(self) -> dict[str, Any]:
        payload = {
            "available": self.available,
            "cli_version": self.cli_version,
            "pipeline": self.pipeline if self.pipeline in {"yes", "no", "unknown"} else "unknown",
            "editor_running": self.editor_running,
            "play_mode": self.play_mode,
            "project_name": self.project_name,
            "detail": scrub_text(self.detail),
        }
        if set(payload) != PUBLIC_KEYS:
            raise RuntimeError("unity status payload drifted from the allow-list")
        return payload


def probe_status(settings: Settings, *, cli: UnityCli | None = None) -> UnityStatus:
    """Feature-detect the CLI and, when present, Editor / Pipeline state."""
    tool = cli or UnityCli()
    configured = settings.unity_cli.project
    shown = settings.unity_cli.project_display_name()
    if not tool.available():
        return UnityStatus(
            available=False,
            pipeline="unknown",
            project_name=shown,
            detail=(
                "unity CLI is not on PATH. Open the Editor and press Play "
                "so Wire can listen (docs/wire-setup.md)."
            ),
        )

    timeout = settings.unity_cli.probe_timeout_s
    version_run = tool.run(["--version", "--json", "--no-banner"], timeout_s=timeout)
    if version_run.timed_out:
        return UnityStatus(
            available=True,
            project_name=shown,
            detail="unity CLI timed out.",
        )
    if version_run.missing:
        return UnityStatus(
            available=False,
            project_name=shown,
            detail=(
                "unity CLI is not on PATH. Open the Editor and press Play "
                "so Wire can listen (docs/wire-setup.md)."
            ),
        )

    editors_run = tool.run(
        ["editors", "running", *_JSON_FLAGS],
        timeout_s=timeout,
    )
    if editors_run.timed_out:
        return UnityStatus(
            available=True,
            cli_version=_version_of(version_run),
            project_name=shown,
            detail="unity CLI timed out.",
        )

    editors = _editor_list(editors_run.payload())
    running = bool(editors) if editors_run.returncode == 0 else None
    matched, playing, running_name = _match_project(editors, configured)
    pipeline = "unknown"
    if running is False:
        pipeline = "no"
    elif running is True:
        status_run = tool.run(["status", *_JSON_FLAGS], timeout_s=timeout)
        pipeline = _pipeline_of(status_run)
        if playing is None and pipeline == "yes":
            play_run = tool.run(
                ["command", "editor_status", *_JSON_FLAGS],
                timeout_s=timeout,
                extra_env=_project_env(configured),
            )
            playing = _play_from_payload(play_run.payload())

    detail = ""
    if editors_run.returncode not in (0, None) and editors_run.returncode != 0:
        if editors_run.returncode == 130:
            detail = "unity editors running interrupted (exit 130)."
        elif running is None:
            detail = f"unity editors running failed (exit {editors_run.returncode})."

    return UnityStatus(
        available=True,
        cli_version=_version_of(version_run),
        pipeline=pipeline,
        editor_running=running,
        play_mode=playing if running else (False if running is False else playing),
        project_name=shown or running_name,
        detail=detail,
        project_open=matched,
    )


def _project_env(project: str | None) -> dict[str, str]:
    if not project:
        return {}
    return {"UNITY_PROJECT_PATH": project}


def _version_of(run: UnityRun) -> str | None:
    payload = run.payload()
    candidates: list[Any] = []
    data = _unwrap(payload)
    if isinstance(data, str):
        candidates.append(data)
    elif isinstance(data, dict):
        for key in ("version", "cliVersion", "cli_version"):
            if key in data:
                candidates.append(data[key])
    line = (run.stdout or "").strip().splitlines()
    if line:
        candidates.append(line[0].strip())
    for item in candidates:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if _VERSION_RE.match(text) and not _SENSITIVE.search(text):
            return text[:80]
    return None


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload and (
        "success" in payload or "command" in payload or "errors" in payload
    ):
        return payload["data"]
    return payload


def _editor_list(payload: Any) -> list[dict[str, Any]]:
    data = _unwrap(payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        for key in ("editors", "items", "running"):
            val = data.get(key)
            if isinstance(val, list):
                return [item for item in val if isinstance(item, dict)]
        if any(key in data for key in ("projectPath", "project_path", "pid", "processId")):
            return [data]
    return []


def _editor_project(editor: dict[str, Any]) -> str | None:
    for key in _PROJECT_KEYS:
        val = editor.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, dict):
            inner = val.get("path") or val.get("name")
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    return None


def _boolish(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "playing", "play"}:
            return True
        if lowered in {"false", "no", "stopped", "stop", "edit"}:
            return False
    return None


def _play_flag(editor: dict[str, Any]) -> bool | None:
    for key in _PLAY_KEYS:
        if key in editor:
            parsed = _boolish(editor[key])
            if parsed is not None:
                return parsed
    return None


def _play_from_payload(payload: Any) -> bool | None:
    data = _unwrap(payload)
    if isinstance(data, dict):
        flag = _play_flag(data)
        if flag is not None:
            return flag
        for key in ("editor", "status", "result"):
            nested = data.get(key)
            if isinstance(nested, dict):
                flag = _play_flag(nested)
                if flag is not None:
                    return flag
    return None


def _match_project(
    editors: list[dict[str, Any]],
    configured: str | None,
) -> tuple[bool, bool | None, str | None]:
    """Return (configured project is open, play mode, display name)."""
    if not editors:
        return False, None, None
    if configured:
        for editor in editors:
            reported = _editor_project(editor)
            if reported and _same_project(configured, reported):
                return True, _play_flag(editor), display_name(configured)
        return False, None, display_name(configured)
    first = editors[0]
    return False, _play_flag(first), display_name(_editor_project(first))


def _same_project(configured: str, reported: str) -> bool:
    try:
        return Path(configured).expanduser().resolve() == Path(reported).expanduser().resolve()
    except OSError:
        return False


def _pipeline_of(run: UnityRun) -> str:
    if run.timed_out or run.missing:
        return "unknown"
    if run.returncode == 130:
        return "unknown"
    data = _unwrap(run.payload())
    state = ""
    if isinstance(data, dict):
        raw = data.get("state") or data.get("status") or data.get("connection")
        if isinstance(raw, str):
            state = raw.strip().lower()
        if data.get("reachable") is True or data.get("connected") is True:
            return "yes"
    if state in _READY_STATES:
        return "yes"
    if run.returncode == 0 and state == "":
        return "yes"
    if run.returncode not in (0, None):
        return "no"
    return "unknown"
