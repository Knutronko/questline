"""HtmlReporter — static single-file HTML artifact per run."""

from __future__ import annotations

import html
import logging
from pathlib import Path

from questline.core.events import Event, RunFinished, RunStarted, TestFinished
from questline.reporters.allowlist import allowlisted_context
from questline.reporters.port import RunSummary

logger = logging.getLogger("questline.reporters.html")


class HtmlReporter:
    """Writes ``.questline/artifacts/report-<run_id>.html`` on finalize."""

    def __init__(self, *, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.last_path: Path | None = None
        self._run_id = ""
        self._profile = ""
        self._tests: list[dict[str, str]] = []

    def on_event(self, event: Event) -> None:
        if isinstance(event, RunStarted):
            self._run_id = event.run_id
            self._profile = event.profile
            self._tests = []
        elif isinstance(event, TestFinished):
            ctx = allowlisted_context(
                {
                    "test_id": event.test_id,
                    "nodeid": event.nodeid,
                    "status": event.status,
                    "verdict": event.verdict,
                    "error_type": event.error_type,
                    "error_message": event.error_message,
                    "duration_s": event.duration_s,
                }
            )
            self._tests.append(ctx)
        elif isinstance(event, RunFinished):
            pass

    def finalize(self, run_summary: RunSummary) -> None:
        run_id = run_summary.run_id or self._run_id or "unknown"
        path = self.output_dir / f"report-{run_id}.html"
        body = _render_html(run_summary, fallback_tests=self._tests)
        path.write_text(body, encoding="utf-8")
        self.last_path = path
        logger.info("HTML report written to %s", path)


def _render_html(summary: RunSummary, *, fallback_tests: list[dict[str, str]]) -> str:
    meta = allowlisted_context(
        {
            "run_id": summary.run_id,
            "profile": summary.profile,
            "status": summary.status,
            "duration_s": summary.duration_s,
            "driver": summary.driver,
            "device": summary.device,
            "passed": summary.passed,
            "failed": summary.failed,
            "skipped": summary.skipped,
            "error": summary.error,
            "total": summary.total,
            "infra_failures": summary.infra_failures,
            "test_failures": summary.test_failures,
            "authoring_failures": summary.authoring_failures,
            "unknown_failures": summary.unknown_failures,
        }
    )
    rows = ""
    if summary.tests:
        for t in summary.tests:
            rows += _test_row(
                allowlisted_context(
                    {
                        "nodeid": t.nodeid,
                        "status": t.status,
                        "verdict": t.verdict,
                        "error_type": t.error_type,
                        "error_message": t.error_message,
                        "duration_s": t.duration_s,
                        "death_step_name": t.death_step_name,
                    }
                )
            )
    else:
        for t in fallback_tests:
            rows += _test_row(t)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Questline report {html.escape(meta.get("run_id", ""))}</title>
<style>
  :root {{ --bg:#0f1419; --fg:#e7ecf1; --muted:#9aa7b5; --ok:#3dd68c; --bad:#f07178;
           --infra:#e6b450; --card:#1a2332; --line:#2a3544; }}
  body {{ font-family: "Segoe UI", system-ui, sans-serif; background: var(--bg);
         color: var(--fg); margin: 0; padding: 2rem; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 .25rem; }}
  .meta {{ color: var(--muted); margin-bottom: 1.5rem; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: .75rem; margin-bottom: 1.5rem; }}
  .stat {{ background: var(--card); border: 1px solid var(--line); padding: .75rem 1rem;
           min-width: 6rem; }}
  .stat b {{ display: block; font-size: 1.25rem; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card); }}
  th, td {{ text-align: left; padding: .55rem .75rem; border-bottom: 1px solid var(--line);
            vertical-align: top; font-size: .9rem; }}
  th {{ color: var(--muted); font-weight: 600; }}
  .passed {{ color: var(--ok); }}
  .failed, .error {{ color: var(--bad); }}
  .verdict-infra {{ color: var(--infra); }}
  .verdict-test {{ color: var(--bad); }}
</style>
</head>
<body>
  <h1>Questline run</h1>
  <div class="meta">
    run_id={html.escape(meta.get("run_id", ""))} ·
    profile={html.escape(meta.get("profile", ""))} ·
    status={html.escape(meta.get("status", ""))} ·
    duration={html.escape(meta.get("duration_s", ""))}s ·
    driver={html.escape(meta.get("driver", "") or "—")} ·
    device={html.escape(meta.get("device", "") or "—")}
  </div>
  <div class="grid">
    {_stat("passed", meta.get("passed", "0"))}
    {_stat("failed", meta.get("failed", "0"))}
    {_stat("skipped", meta.get("skipped", "0"))}
    {_stat("infra", meta.get("infra_failures", "0"))}
    {_stat("test", meta.get("test_failures", "0"))}
  </div>
  <table>
    <thead>
      <tr><th>Test</th><th>Status</th><th>Verdict</th><th>Error</th><th>Death step</th></tr>
    </thead>
    <tbody>
      {rows or '<tr><td colspan="5">No tests recorded.</td></tr>'}
    </tbody>
  </table>
</body>
</html>
"""


def _stat(label: str, value: str) -> str:
    return f'<div class="stat"><b>{html.escape(value)}</b>{html.escape(label)}</div>'


def _test_row(ctx: dict[str, str]) -> str:
    status = ctx.get("status", "")
    verdict = ctx.get("verdict", "")
    err = " ".join(
        p for p in (ctx.get("error_type", ""), ctx.get("error_message", "")) if p
    ).strip()
    return (
        "<tr>"
        f'<td>{html.escape(ctx.get("nodeid", ""))}</td>'
        f'<td class="{html.escape(status)}">{html.escape(status)}</td>'
        f'<td class="verdict-{html.escape(verdict)}">{html.escape(verdict)}</td>'
        f"<td>{html.escape(err)}</td>"
        f'<td>{html.escape(ctx.get("death_step_name", ""))}</td>'
        "</tr>\n"
    )
