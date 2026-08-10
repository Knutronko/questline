"""Allow-list rendering for anything that leaves the machine (master plan §3.8)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

# Fields that Slack / GitHub Issues / HTML exporters may ever emit.
# Paths, env dumps, artifact locations, and raw tags are intentionally absent.
ALLOWED_EXPORT_FIELDS: frozenset[str] = frozenset(
    {
        "run_id",
        "profile",
        "status",
        "duration_s",
        "driver",
        "device",
        "passed",
        "failed",
        "skipped",
        "error",
        "total",
        "infra_failures",
        "test_failures",
        "authoring_failures",
        "unknown_failures",
        "test_id",
        "nodeid",
        "verdict",
        "error_type",
        "error_message",
        "death_step_name",
        "feature_id",
        "suite",
        "signature",
        "issue_title",
        "html_path",
    }
)

_PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def allowlisted_context(raw: Mapping[str, Any]) -> dict[str, str]:
    """Return only allow-listed keys, stringified. Unknown keys are dropped."""
    out: dict[str, str] = {}
    for key, value in raw.items():
        if key not in ALLOWED_EXPORT_FIELDS:
            continue
        if value is None:
            out[key] = ""
        else:
            out[key] = str(value)
    return out


def render_template(template: str, context: Mapping[str, Any]) -> str:
    """Render ``{{field}}`` placeholders using an allow-listed context only.

    Placeholders for non-allow-listed fields are replaced with empty string
    (never interpolated from *context*). Extra context keys are ignored.
    """
    safe = allowlisted_context(context)

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in ALLOWED_EXPORT_FIELDS:
            return ""
        return safe.get(name, "")

    return _PLACEHOLDER.sub(_replace, template)
