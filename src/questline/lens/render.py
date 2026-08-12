"""Human-readable rendering for GameLens diffs."""

from __future__ import annotations

from questline.lens.diff import DiffEntry, DiffReport
from questline.lens.report import ImplicationsReport


def render_diff_text(report: DiffReport, *, implications: ImplicationsReport | None = None) -> str:
    # ASCII-only: Windows consoles often use cp1252 and break on arrows / delta glyphs.
    lines: list[str] = [
        f"GameLens diff: {report.version_a} -> {report.version_b}",
    ]
    if report.snapshot_id_a or report.snapshot_id_b:
        lines.append(
            f"snapshots: {report.snapshot_id_a or '?'} -> {report.snapshot_id_b or '?'}"
        )
    if report.feature_id:
        lines.append(f"feature_id: {report.feature_id}")
    lines.append(f"entries: {len(report.entries)}")
    lines.append("")

    grouped = report.by_system()
    if not grouped:
        lines.append("(no differences)")
    for system in sorted(grouped):
        lines.append(f"[{system}]")
        for entry in grouped[system]:
            lines.append(f"  {_format_entry(entry)}")
        lines.append("")

    if implications is not None:
        lines.append("--- AI implications ---")
        lines.append(f"status: {implications.status}")
        if implications.pending:
            lines.append(f"pending: {implications.pending}")
        lines.append(f"framing: {implications.framing}")
        lines.append(implications.summary)
        lines.append("")

    return "\n".join(lines)


def _format_entry(entry: DiffEntry) -> str:
    if entry.kind == "added_entity":
        return f"+ entity {entry.entity_id} (new)"
    if entry.kind == "removed_entity":
        return f"- entity {entry.entity_id} (removed)"
    if entry.kind in {"curve_changed", "series_changed"}:
        return f"~ {entry.entity_id}.{entry.path} ({entry.kind})"
    path = entry.path or "?"
    if entry.delta is not None:
        pct = f" ({entry.pct:+.2f}%)" if entry.pct is not None else ""
        return (
            f"~ {entry.entity_id}.{path}: {entry.before} -> {entry.after} "
            f"(delta {entry.delta:+g}{pct})"
        )
    return f"~ {entry.entity_id}.{path}: {entry.before!r} -> {entry.after!r}"
