"""ASCII-only telemetry CLI text (Windows cp1252-safe; INC-0007)."""

from __future__ import annotations

from typing import Any


def render_session_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "no telemetry sessions\n"
    lines = [
        "id                       version    snapshot   policy     seed  outcome  events",
        "-" * 86,
    ]
    for row in rows:
        summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
        counts = summary.get("event_counts") if isinstance(summary, dict) else {}
        n = sum(int(v) for v in counts.values()) if isinstance(counts, dict) else "?"
        lines.append(
            f"{_cell(row.get('id'), 24)} {_cell(row.get('game_version'), 10)} "
            f"{_cell(row.get('config_snapshot_id'), 10)} {_cell(row.get('policy_id'), 10)} "
            f"{_cell(row.get('seed'), 5)} {_cell(row.get('outcome'), 8)} {n}"
        )
    return "\n".join(lines) + "\n"


def render_session_detail(row: dict[str, Any], event_count: int) -> str:
    summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
    lines = [
        f"id:         {row.get('id')}",
        f"version:    {row.get('game_version')}",
        f"snapshot:   {row.get('config_snapshot_id') or '-'}",
        f"policy:     {row.get('policy_id') or '-'}",
        f"seed:       {row.get('seed') or '-'}",
        f"feature:    {row.get('feature_id') or '-'}",
        f"source:     {row.get('source')}",
        f"outcome:    {row.get('outcome') or '-'}",
        f"started:    {row.get('started_at')}",
        f"finished:   {row.get('finished_at') or '-'}",
        f"events:     {event_count}",
        f"artifact:   {row.get('artifact_path') or '-'}",
    ]
    if summary:
        lines.append("summary:")
        for key in (
            "deploy_count",
            "skill_casts",
            "repair_count",
            "leak_count",
            "time_to_first_leak",
            "waves_started",
            "waves_completed",
            "duration_s",
            "dropped_count",
        ):
            lines.append(f"  {key}: {summary.get(key)}")
        nets = summary.get("currency_net") or {}
        if nets:
            lines.append(f"  currency_net: {nets}")
        unknown = summary.get("unknown_event_names") or []
        if unknown:
            lines.append(f"  unknown_event_names: {unknown}")
        labels = summary.get("checkpoint_labels") or []
        if labels:
            lines.append(f"  checkpoint_labels: {labels}")
    return "\n".join(lines) + "\n"


def render_compare(id_a: str, id_b: str, deltas: dict[str, Any]) -> str:
    lines = [f"compare {id_a} -> {id_b} (b-a)", "-" * 40]
    for key, value in deltas.items():
        if key == "outcome":
            lines.append(f"outcome: {value.get('a')} -> {value.get('b')}")
        elif isinstance(value, dict):
            if value:
                lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def _cell(value: Any, width: int) -> str:
    text = "-" if value is None or value == "" else str(value)
    if len(text) > width:
        text = text[: width - 1] + "+"
    return text.ljust(width)
