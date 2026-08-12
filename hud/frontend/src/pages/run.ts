import { esc, fmtDur, getRun } from "../api";

export async function renderRun(runId: string): Promise<string> {
  const data = await getRun(runId);
  const r = data.run;
  const b = data.banner;
  const rows = data.tests
    .map(
      (t) => `
    <tr data-testid="test-row" data-test-id="${esc(t.id)}">
      <td class="wrap"><a href="#/runs/${encodeURIComponent(runId)}/tests/${encodeURIComponent(t.id)}">${esc(t.nodeid)}</a></td>
      <td><span class="badge ${esc(t.status)}">${esc(t.status)}</span></td>
      <td class="verdict-${esc(t.verdict ?? "")}">${esc(t.verdict ?? "—")}</td>
      <td>${esc(fmtDur(t.duration_s))}</td>
      <td class="wrap">${esc(t.death_step_name ?? "")}</td>
    </tr>`,
    )
    .join("");

  return `
    <p class="meta"><a href="#/">← Runs</a> · ${esc(r.id)}</p>
    <h1>Run detail</h1>
    <div class="meta">
      profile=${esc(r.profile)} · driver=${esc(r.driver ?? "—")} ·
      device=${esc(r.device ?? "—")} · status=${esc(r.status)} ·
      duration=${esc(fmtDur(r.duration_s))}
    </div>
    <div class="banner" data-testid="verdict-banner">
      <div class="stat ok"><span>passed</span><b>${r.passed}</b></div>
      <div class="stat"><span>failed</span><b>${r.failed}</b></div>
      <div class="stat infra"><span>infra</span><b>${b.infra_failures}</b></div>
      <div class="stat test"><span>test</span><b>${b.test_failures}</b></div>
      <div class="stat"><span>authoring</span><b>${b.authoring_failures}</b></div>
    </div>
    <h2>Tests</h2>
    <div class="table-wrap">
      <table data-testid="tests-table">
        <thead>
          <tr><th>Test</th><th>Status</th><th>Verdict</th><th>Duration</th><th>Death step</th></tr>
        </thead>
        <tbody>${
          rows ||
          `<tr><td colspan="5">${
            r.status === "failed" || r.status === "error"
              ? "No tests recorded — session setup failed before any test ran (often adb device lock or Wire connect). Open <a href=\"#/launch\">Launch</a> Status → <code>error</code> / <code>log_tail</code>."
              : "No tests."
          }</td></tr>`
        }</tbody>
      </table>
    </div>
  `;
}
