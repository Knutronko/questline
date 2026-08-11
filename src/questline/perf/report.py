"""Text / HTML summaries for ``questline perf report``."""

from __future__ import annotations

import html
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

Format = Literal["text", "html"]


def summarize_perf_samples(samples: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    """Group samples by metric → count/min/max/avg/p50."""
    by_metric: dict[str, list[float]] = defaultdict(list)
    for row in samples:
        metric = str(row.get("metric") or "")
        if not metric:
            continue
        try:
            by_metric[metric].append(float(row["value"]))
        except (KeyError, TypeError, ValueError):
            continue
    out: dict[str, dict[str, float | int]] = {}
    for metric, values in sorted(by_metric.items()):
        if not values:
            continue
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2:
            p50 = sorted_vals[mid]
        else:
            p50 = (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        out[metric] = {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": statistics.fmean(values),
            "p50": p50,
        }
    return out


def render_perf_report(
    *,
    run_id: str,
    samples: list[dict[str, Any]],
    fmt: Format = "text",
) -> str:
    summary = summarize_perf_samples(samples)
    if fmt == "html":
        return _html(run_id, summary, sample_count=len(samples))
    return _text(run_id, summary, sample_count=len(samples))


def write_perf_report(
    *,
    run_id: str,
    samples: list[dict[str, Any]],
    output_dir: Path,
    fmt: Format = "text",
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    body = render_perf_report(run_id=run_id, samples=samples, fmt=fmt)
    ext = "html" if fmt == "html" else "txt"
    path = output_dir / f"perf-report-{run_id}.{ext}"
    path.write_text(body, encoding="utf-8")
    return path


def _text(run_id: str, summary: dict[str, dict[str, float | int]], *, sample_count: int) -> str:
    lines = [
        f"Questline perf report — run {run_id}",
        f"samples: {sample_count}",
        "",
    ]
    if not summary:
        lines.append("(no perf samples)")
        return "\n".join(lines) + "\n"
    lines.append(f"{'metric':<20} {'n':>6} {'min':>10} {'avg':>10} {'p50':>10} {'max':>10}")
    lines.append("-" * 70)
    for metric, stats in summary.items():
        lines.append(
            f"{metric:<20} {stats['count']:>6} "
            f"{stats['min']:>10.3f} {stats['avg']:>10.3f} "
            f"{stats['p50']:>10.3f} {stats['max']:>10.3f}"
        )
    return "\n".join(lines) + "\n"


def _html(run_id: str, summary: dict[str, dict[str, float | int]], *, sample_count: int) -> str:
    rows = ""
    for metric, stats in summary.items():
        rows += (
            "<tr>"
            f"<td>{html.escape(metric)}</td>"
            f"<td>{stats['count']}</td>"
            f"<td>{stats['min']:.3f}</td>"
            f"<td>{stats['avg']:.3f}</td>"
            f"<td>{stats['p50']:.3f}</td>"
            f"<td>{stats['max']:.3f}</td>"
            "</tr>"
        )
    if not rows:
        rows = '<tr><td colspan="6">(no perf samples)</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Perf report {html.escape(run_id)}</title>
<style>
body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; }}
th, td {{ border: 1px solid #ccc; padding: 0.35rem 0.6rem; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ background: #f4f4f4; }}
</style></head><body>
<h1>Questline perf report</h1>
<p>run <code>{html.escape(run_id)}</code> — {sample_count} samples</p>
<table>
<thead><tr><th>metric</th><th>n</th><th>min</th><th>avg</th><th>p50</th><th>max</th></tr></thead>
<tbody>{rows}</tbody>
</table>
</body></html>
"""
