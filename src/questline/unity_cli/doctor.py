"""``questline doctor`` row for the Unity CLI sidecar."""

from __future__ import annotations

from typing import Any

from questline.core.config import Settings
from questline.unity_cli.client import UnityCli
from questline.unity_cli.status import UnityStatus, probe_status


def _tri(value: bool | None) -> str:
    if value is None:
        return "?"
    return str(value).lower()


def doctor_lines(settings: Settings, *, cli: UnityCli | None = None) -> list[str]:
    """One allow-listed summary. Project is a basename, never a home path."""
    status = probe_status(settings, cli=cli)
    return _format(status)


def status_public(settings: Settings, *, cli: UnityCli | None = None) -> dict[str, Any]:
    return probe_status(settings, cli=cli).to_public()


def _format(status: UnityStatus) -> list[str]:
    version = status.cli_version or "-"
    project = status.project_name or "-"
    lines = [
        (
            f"unity_cli:   available={str(status.available).lower()} version={version} "
            f"pipeline={status.pipeline} editor={_tri(status.editor_running)} "
            f"play={_tri(status.play_mode)} project={project}"
        )
    ]
    if status.detail:
        lines.append(f"             {status.detail}")
    return lines
