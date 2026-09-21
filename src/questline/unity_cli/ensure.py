"""Open the configured Unity project, enter Play, and wait for Wire."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from questline.core.config import Settings
from questline.core.errors import InfraError
from questline.unity_cli.client import UnityCli, UnityRun
from questline.unity_cli.status import UnityStatus, probe_status, scrub_text
from questline.unity_cli.wire_wait import wait_for_editor_wire

logger = logging.getLogger("questline.unity_cli")

_JSON_FLAGS = ("--json", "--non-interactive", "--no-banner")
WaitWire = Callable[..., None]


@dataclass
class EnsureResult:
    ok: bool
    skipped: bool
    wire_ready: bool
    detail: str
    unity: UnityStatus

    def to_public(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "skipped": self.skipped,
            "wire_ready": self.wire_ready,
            "detail": scrub_text(self.detail),
            "unity": self.unity.to_public(),
        }


def ensure_editor(
    settings: Settings,
    *,
    cli: UnityCli | None = None,
    wait_wire: WaitWire | None = None,
) -> EnsureResult:
    """Idempotent Editor ensure. Missing CLI skips; it does not raise.

    Android / adb profiles are not started here. Live tests stay on Wire.
    """
    tool = cli or UnityCli()
    waiter = wait_wire or wait_for_editor_wire
    status = probe_status(settings, cli=tool)
    if not status.available:
        return EnsureResult(
            ok=False,
            skipped=True,
            wire_ready=False,
            detail=status.detail,
            unity=status,
        )

    project = settings.unity_cli.project
    if not project:
        return EnsureResult(
            ok=False,
            skipped=True,
            wire_ready=False,
            detail=(
                "unity_cli.project is unset. Open the Editor and press Play "
                "so Wire can listen (docs/wire-setup.md)."
            ),
            unity=status,
        )

    env = {"UNITY_PROJECT_PATH": project}
    timeout = settings.unity_cli.command_timeout_s
    if not status.project_open:
        opened = tool.run(
            ["open", project, *_JSON_FLAGS],
            timeout_s=timeout,
            extra_env=env,
        )
        failed = _fail_run(opened, "unity open")
        if failed:
            return _failed(status, failed)

    if status.play_mode is not True:
        played = tool.run(
            ["command", "editor_play", *_JSON_FLAGS],
            timeout_s=timeout,
            extra_env=env,
        )
        failed = _fail_run(played, "unity command editor_play")
        if failed:
            return _failed(status, failed)

    try:
        waiter(
            host=settings.target_host,
            port=settings.target_port,
            timeout_s=settings.unity_cli.wire_timeout_s,
            interval_s=settings.wait.interval,
        )
    except InfraError as exc:
        return _failed(status, scrub_text(str(exc)) or "Wire hello failed.")

    ready = probe_status(settings, cli=tool)
    return EnsureResult(
        ok=True,
        skipped=False,
        wire_ready=True,
        detail="Editor is in Play mode and Wire hello succeeded.",
        unity=ready,
    )


def maybe_ensure_editor(
    settings: Settings,
    *,
    ensure: Callable[[Settings], EnsureResult] | None = None,
) -> EnsureResult | None:
    """Pytest hook: only editor + ``driver=questline`` when the flag is on.

    Default ``ensure_editor`` is false, so mock CI never launches Unity.
    A missing CLI is a warning. A Wire timeout is an infra error.
    """
    if not settings.unity_cli.ensure_editor:
        return None
    if (settings.driver or "").lower() != "questline":
        return None
    if (settings.device or "").lower() in {"adb", "android"}:
        return None
    if (settings.target_platform or "editor").lower() != "editor":
        return None
    fn = ensure or ensure_editor
    result = fn(settings)
    if result.skipped:
        logger.warning("unity ensure-editor skipped: %s", result.detail)
        return result
    if not result.ok:
        raise InfraError(result.detail or "unity ensure-editor failed")
    return result


def _fail_run(run: UnityRun, label: str) -> str | None:
    if run.timed_out:
        return f"{label} timed out."
    if run.missing:
        return "unity CLI is not on PATH. Open the Editor and press Play so Wire can listen."
    code = run.returncode
    if code in (0, None):
        return None
    if code == 130:
        return f"{label} interrupted (exit 130)."
    return f"{label} failed (exit {code})."


def _failed(status: UnityStatus, detail: str) -> EnsureResult:
    return EnsureResult(
        ok=False,
        skipped=False,
        wire_ready=False,
        detail=detail,
        unity=status,
    )
