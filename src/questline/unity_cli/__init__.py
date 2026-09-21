"""Unity CLI sidecar — Editor lifecycle, not a DriverPort (ADR-0012)."""

from questline.unity_cli.doctor import doctor_lines, status_public
from questline.unity_cli.ensure import EnsureResult, ensure_editor, maybe_ensure_editor
from questline.unity_cli.status import UnityStatus, probe_status

__all__ = [
    "EnsureResult",
    "UnityStatus",
    "doctor_lines",
    "ensure_editor",
    "maybe_ensure_editor",
    "probe_status",
    "status_public",
]
