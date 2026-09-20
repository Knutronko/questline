"""Triage digest via ReporterPort (HTML section + Slack thread)."""

from __future__ import annotations

import html

from questline.ai.agents.task import AgentTask
from questline.core.store import RunStore
from questline.reporters.html import HtmlReporter
from questline.reporters.port import ReporterPort, RunSummary
from questline.reporters.slack.reporter import SlackReporter


def render_digest_text(task: AgentTask) -> str:
    lines = [
        f"Triage digest for run {task.run_id or '?'}",
        f"verdict={task.verdict} cause={task.cause} status={task.status}",
        "",
        (task.summary or "").strip(),
        "",
        "Clusters:",
    ]
    for cluster in task.clusters:
        n = len(cluster.get("test_ids") or [])
        lines.append(
            f"- [{cluster.get('bucket')}] {cluster.get('error_type')} "
            f"x{n}: {cluster.get('signature')}"
        )
        hypo = cluster.get("hypothesis")
        if hypo:
            lines.append(f"  hypothesis: {hypo}")
    return "\n".join(lines).strip() + "\n"


def render_digest_html(task: AgentTask) -> str:
    rows = ""
    for cluster in task.clusters:
        n = len(cluster.get("test_ids") or [])
        rows += (
            "<tr>"
            f"<td>{html.escape(str(cluster.get('bucket') or ''))}</td>"
            f"<td>{html.escape(str(cluster.get('error_type') or ''))}</td>"
            f"<td>{n}</td>"
            f"<td>{html.escape(str(cluster.get('signature') or ''))}</td>"
            f"<td>{html.escape(str(cluster.get('hypothesis') or ''))}</td>"
            "</tr>"
        )
    rid = html.escape(str(task.run_id or ""))
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Triage {rid}</title>
<style>
body{{font-family:sans-serif;background:#0f1419;color:#e7ecf1;padding:1.5rem}}
table{{border-collapse:collapse;width:100%}}
th,td{{border-bottom:1px solid #2a3544;padding:.4rem;text-align:left}}
</style>
</head><body>
<h1>Triage digest</h1>
<p>run={html.escape(str(task.run_id or ''))} · verdict={html.escape(str(task.verdict or ''))}
 · cause={html.escape(str(task.cause or ''))}</p>
<p>{html.escape(task.summary or '')}</p>
<table><thead><tr><th>Bucket</th><th>Error</th><th>N</th><th>Signature</th><th>Hypothesis</th></tr></thead>
<tbody>{rows or '<tr><td colspan="5">No clusters.</td></tr>'}</tbody></table>
</body></html>
"""


def emit_triage_digest(
    task: AgentTask,
    *,
    store: RunStore,
    reporters: list[ReporterPort],
) -> None:
    dest = store.artifacts_dir / "agents" / task.id
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "digest.md").write_text(render_digest_text(task), encoding="utf-8")
    html_path = dest / "digest.html"
    html_path.write_text(render_digest_html(task), encoding="utf-8")
    extras = {"triage_digest": str(html_path), "triage_task_id": task.id}
    summary = RunSummary(
        run_id=task.run_id or task.id,
        profile="agent",
        status=task.status,
        extras=extras,
    )
    text = render_digest_text(task)
    for reporter in reporters:
        if isinstance(reporter, HtmlReporter):
            path = reporter.output_dir / f"triage-{task.run_id or task.id}.html"
            path.write_text(render_digest_html(task), encoding="utf-8")
            reporter.last_path = path
            continue
        if isinstance(reporter, SlackReporter):
            _slack_digest(reporter, text)
            continue
        try:
            reporter.finalize(summary)
        except Exception:
            continue


def _slack_digest(reporter: SlackReporter, text: str) -> None:
    if reporter._use_webhook:
        reporter.transport.post_webhook(text=text)
        return
    channel = reporter._channel or reporter.channel
    if reporter._start_ts and channel:
        reporter.transport.post_reply(channel=channel, thread_ts=reporter._start_ts, text=text)
        return
    reporter.transport.post_message(text=text, channel=channel)
