"""QuestlineWire protocol constants and request helpers (ADR-0005 / ADR-0008)."""

from __future__ import annotations

import json
import uuid
from typing import Any

# NDJSON envelope field ``v`` — framing version (stable across Wire MVP + v2).
ENVELOPE_VERSION = 1

# Capability advertised in ``hello.result.protocol_version`` (Wire v2 UI = 2).
PROTOCOL_VERSION = 2

FEATURE_HOOKS = "hooks"
FEATURE_UI = "ui"
DEFAULT_FEATURES: tuple[str, ...] = (FEATURE_HOOKS, FEATURE_UI)

OPS = frozenset(
    {
        "hello",
        "ping",
        "app_state",
        "hooks_manifest",
        "call_hook",
        "hierarchy",
        "find",
        "find_all",
        "tap",
        "screenshot",
    }
)

# Hierarchy reply bounds (companion + FakeWire must enforce).
DEFAULT_MAX_DEPTH = 32
DEFAULT_MAX_NODES = 500


def make_request(
    op: str, params: dict[str, Any] | None = None, *, req_id: str | None = None
) -> str:
    """Serialize one NDJSON request line (without trailing newline)."""
    if op not in OPS:
        raise ValueError(f"unknown wire op: {op}")
    payload = {
        "v": ENVELOPE_VERSION,
        "id": req_id or uuid.uuid4().hex,
        "op": op,
        "params": params or {},
    }
    return json.dumps(payload, separators=(",", ":"))


def parse_response(line: str) -> dict[str, Any]:
    """Parse one NDJSON response object."""
    data = json.loads(line)
    if not isinstance(data, dict):
        raise ValueError("wire response must be a JSON object")
    return data


def hello_advertises_ui(hello: dict[str, Any]) -> bool:
    """True when companion hello advertises Wire v2 UI capability."""
    features = hello.get("features")
    if isinstance(features, list) and FEATURE_UI in features:
        return True
    version = hello.get("protocol_version")
    try:
        return int(version) >= 2
    except (TypeError, ValueError):
        return False
