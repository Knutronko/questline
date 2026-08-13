"""Session summary rollup from thin telemetry events (measured facts only)."""

from __future__ import annotations

from typing import Any

from questline.telemetry.schema import THIN_EVENT_NAMES


def compute_summary(
    events: list[dict[str, Any]],
    *,
    outcome: str | None = None,
    dropped_count: int = 0,
) -> dict[str, Any]:
    """Aggregate catalog events. Unknown names are listed, not rolled up."""
    counts: dict[str, int] = {}
    unknown: list[str] = []
    currency_in: dict[str, float] = {}
    currency_out: dict[str, float] = {}
    leak_count = 0
    time_to_first_leak: float | None = None
    waves_started = 0
    waves_completed = 0
    deploy_count = 0
    skill_casts = 0
    repair_count = 0
    checkpoint_labels: list[str] = []
    duration_s: float | None = None
    end_outcome = outcome

    for ev in events:
        name = str(ev.get("name", ""))
        counts[name] = counts.get(name, 0) + 1
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        t = float(ev.get("t") or 0.0)

        if name not in THIN_EVENT_NAMES:
            if name not in unknown:
                unknown.append(name)
            continue

        if name == "currency.earned":
            cid = str(payload.get("currency_id") or "")
            amt = _num(payload.get("amount"))
            if cid and amt is not None:
                currency_in[cid] = currency_in.get(cid, 0.0) + amt
        elif name == "currency.spent":
            cid = str(payload.get("currency_id") or "")
            amt = _num(payload.get("amount"))
            if cid and amt is not None:
                currency_out[cid] = currency_out.get(cid, 0.0) + amt
        elif name == "unit.deployed":
            deploy_count += 1
        elif name == "skill.cast":
            skill_casts += 1
        elif name == "repair.applied":
            repair_count += 1
        elif name == "combat.leak":
            leak_count += 1
            if time_to_first_leak is None:
                time_to_first_leak = t
        elif name == "wave.started":
            waves_started += 1
        elif name == "wave.completed":
            waves_completed += 1
        elif name == "session.checkpoint":
            label = payload.get("label")
            if isinstance(label, str) and label and label not in checkpoint_labels:
                checkpoint_labels.append(label)
        elif name == "session.end":
            duration_s = _num(payload.get("duration_s"))
            if duration_s is None:
                duration_s = t
            out = payload.get("outcome")
            if isinstance(out, str) and out.strip():
                end_outcome = out.strip()

    if duration_s is None and events:
        duration_s = float(events[-1].get("t") or 0.0)

    ids = sorted(set(currency_in) | set(currency_out))
    currency_net = {cid: currency_in.get(cid, 0.0) - currency_out.get(cid, 0.0) for cid in ids}

    return {
        "event_counts": dict(sorted(counts.items())),
        "currency_net": currency_net,
        "currency_in": dict(sorted(currency_in.items())),
        "currency_out": dict(sorted(currency_out.items())),
        "deploy_count": deploy_count,
        "skill_casts": skill_casts,
        "repair_count": repair_count,
        "leak_count": leak_count,
        "time_to_first_leak": time_to_first_leak,
        "waves_started": waves_started,
        "waves_completed": waves_completed,
        "duration_s": duration_s,
        "outcome": end_outcome,
        "checkpoint_labels": checkpoint_labels,
        "dropped_count": dropped_count,
        "unknown_event_names": unknown,
    }


def diff_summaries(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Numeric/count deltas (b - a) for comparable summary fields."""
    numeric_keys = (
        "deploy_count",
        "skill_casts",
        "repair_count",
        "leak_count",
        "time_to_first_leak",
        "waves_started",
        "waves_completed",
        "duration_s",
        "dropped_count",
    )
    deltas: dict[str, Any] = {}
    for key in numeric_keys:
        va, vb = a.get(key), b.get(key)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            deltas[key] = vb - va
        else:
            deltas[key] = {"a": va, "b": vb}

    def _map_delta(ka: dict[str, Any], kb: dict[str, Any]) -> dict[str, float]:
        keys = sorted(set(ka) | set(kb))
        return {k: float(kb.get(k, 0) or 0) - float(ka.get(k, 0) or 0) for k in keys}

    deltas["currency_net"] = _map_delta(
        a.get("currency_net") or {}, b.get("currency_net") or {}
    )
    deltas["currency_in"] = _map_delta(a.get("currency_in") or {}, b.get("currency_in") or {})
    deltas["currency_out"] = _map_delta(
        a.get("currency_out") or {}, b.get("currency_out") or {}
    )
    deltas["event_counts"] = _map_delta(
        a.get("event_counts") or {}, b.get("event_counts") or {}
    )
    deltas["outcome"] = {"a": a.get("outcome"), "b": b.get("outcome")}
    return deltas


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
