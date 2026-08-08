"""QuestlineWire protocol constants and request helpers (ADR-0005)."""

from __future__ import annotations

import json
import uuid
from typing import Any

PROTOCOL_VERSION = 1

OPS = frozenset({"hello", "ping", "app_state", "hooks_manifest", "call_hook"})


def make_request(
    op: str, params: dict[str, Any] | None = None, *, req_id: str | None = None
) -> str:
    """Serialize one NDJSON request line (without trailing newline)."""
    if op not in OPS:
        raise ValueError(f"unknown wire op: {op}")
    payload = {
        "v": PROTOCOL_VERSION,
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
