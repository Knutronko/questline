"""Load / dump telemetry spool JSON (schema_version 1)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from questline.core.errors import AuthoringError
from questline.telemetry.schema import SCHEMA_VERSION, SOURCES

_UTF8_SIG = "utf-8-sig"


def load_spool(path: Path) -> dict[str, Any]:
    """Read a spool file (UTF-8 with or without BOM)."""
    try:
        text = path.read_text(encoding=_UTF8_SIG)
    except OSError as exc:
        raise AuthoringError(f"cannot read telemetry spool: {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AuthoringError(f"telemetry spool is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AuthoringError(f"telemetry spool must be a JSON object: {path}")
    return data


def dump_spool(payload: dict[str, Any], path: Path) -> None:
    """Write spool JSON as UTF-8 without BOM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_bytes(text.encode("utf-8"))


def validate_spool(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize and validate a spool document. Returns a copy-safe dict."""
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise AuthoringError(
            f"unsupported telemetry schema_version={version!r} (expected {SCHEMA_VERSION})"
        )
    session = data.get("session")
    if not isinstance(session, dict):
        raise AuthoringError("telemetry spool.session must be an object")
    events = data.get("events")
    if not isinstance(events, list):
        raise AuthoringError("telemetry spool.events must be an array")

    sid = _opt_str(session.get("id")) or _opt_str(session.get("session_id"))
    if not sid:
        raise AuthoringError("telemetry session.id is required")
    game_version = _opt_str(session.get("game_version"))
    if not game_version:
        raise AuthoringError("telemetry session.game_version is required")

    source = _opt_str(session.get("source")) or "import"
    if source not in SOURCES:
        raise AuthoringError(
            f"telemetry session.source must be one of {sorted(SOURCES)}, got {source!r}"
        )

    started_at = _opt_str(session.get("started_at"))
    if not started_at:
        raise AuthoringError("telemetry session.started_at is required")

    normalized_events = [_validate_event(item, i) for i, item in enumerate(events)]
    for i, ev in enumerate(normalized_events):
        if "seq" not in ev:
            ev["seq"] = i + 1

    seqs = [int(ev["seq"]) for ev in normalized_events]
    if len(seqs) != len(set(seqs)):
        raise AuthoringError("telemetry events have duplicate seq values")

    dropped = session.get("dropped_count", 0)
    if dropped is None:
        dropped = 0
    if not isinstance(dropped, int) or dropped < 0:
        raise AuthoringError("telemetry session.dropped_count must be an integer >= 0")

    out_session = {
        "id": sid,
        "game_version": game_version,
        "git_commit": _opt_str(session.get("git_commit")),
        "feature_id": _opt_str(session.get("feature_id")),
        "config_snapshot_id": _opt_str(session.get("config_snapshot_id")),
        "policy_id": _opt_str(session.get("policy_id")),
        "seed": _opt_str(session.get("seed")),
        "started_at": started_at,
        "finished_at": _opt_str(session.get("finished_at")),
        "outcome": _opt_str(session.get("outcome")),
        "source": source,
        "run_id": _opt_str(session.get("run_id")),
        "dropped_count": dropped,
    }
    return {"schema_version": SCHEMA_VERSION, "session": out_session, "events": normalized_events}


def _validate_event(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise AuthoringError(f"telemetry events[{index}] must be an object")
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise AuthoringError(f"telemetry events[{index}].name must be a non-empty string")
    t = item.get("t")
    if not isinstance(t, (int, float)) or isinstance(t, bool):
        raise AuthoringError(f"telemetry events[{index}].t must be a number")
    payload = item.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise AuthoringError(f"telemetry events[{index}].payload must be an object")
    out: dict[str, Any] = {
        "t": float(t),
        "name": name.strip(),
        "payload": payload,
    }
    seq = item.get("seq")
    if seq is not None:
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
            raise AuthoringError(f"telemetry events[{index}].seq must be an integer >= 1")
        out["seq"] = seq
    _validate_thin_payload(out["name"], out["payload"], index)
    return out


def _validate_thin_payload(name: str, payload: dict[str, Any], index: int) -> None:
    """Required fields for catalog events; extra names are stored as-is."""
    loc = f"events[{index}] ({name})"
    if name == "session.end":
        _require_str(payload, "outcome", loc)
    elif name == "session.checkpoint":
        _require_str(payload, "label", loc)
    elif name in {"currency.earned", "currency.spent"}:
        _require_str(payload, "currency_id", loc)
        amount = payload.get("amount")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
            raise AuthoringError(f"{loc}: amount must be a number > 0")
    elif name == "unit.deployed":
        _require_str(payload, "unit_id", loc)
    elif name in {"wave.started", "wave.completed"}:
        _require_wave_index(payload, loc)
    elif name == "skill.cast":
        _require_str(payload, "skill_id", loc)


def _require_str(payload: dict[str, Any], key: str, loc: str) -> None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AuthoringError(f"{loc}: {key} is required")


def _require_wave_index(payload: dict[str, Any], loc: str) -> None:
    value = payload.get("wave_index")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AuthoringError(f"{loc}: wave_index must be an integer >= 0")


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    text = value.strip()
    return text or None
