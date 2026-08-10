import { esc, fmtDur, getTrends } from "../api";

export async function renderTrends(): Promise<string> {
  const data = await getTrends(50);
  const series = data.series || [];
  const maxDur = Math.max(1, ...series.map((s) => Number(s.duration_s ?? 0) || 0));
  const bars = series
    .map((s) => {
      const rate = s.pass_rate == null ? 0 : Number(s.pass_rate);
      const h = Math.max(4, Math.round(rate * 100));
      const dur = Number(s.duration_s ?? 0);
      const fail = Number(s.failed ?? 0) > 0;
      return `<div class="bar ${fail ? "fail" : ""}" style="height:${h}%">
        <span>${esc(s.run_id)} · ${(rate * 100).toFixed(0)}% · ${esc(fmtDur(dur))}</span>
      </div>`;
    })
    .join("");

  const durBars = series
    .map((s) => {
      const dur = Number(s.duration_s ?? 0);
      const h = Math.max(4, Math.round((dur / maxDur) * 100));
      return `<div class="bar" style="height:${h}%">
        <span>${esc(s.run_id)} · ${esc(fmtDur(dur))}</span>
      </div>`;
    })
    .join("");

  const flaky = (data.flaky_tests || [])
    .map(
      (f) => `<tr>
        <td class="wrap">${esc(f.nodeid)}</td>
        <td>${esc(f.runs)}</td>
        <td>${esc(f.passed)}/${esc(f.failed)}</td>
        <td>${(Number(f.pass_rate) * 100).toFixed(0)}%</td>
        <td>${(Number(f.flake_score) * 100).toFixed(0)}%</td>
      </tr>`,
    )
    .join("");

  return `
    <h1>Trends</h1>
    <h2>Pass rate (recent runs)</h2>
    <div class="chart" data-testid="pass-chart">${bars || "<span class='meta'>no data</span>"}</div>
    <h2>Duration</h2>
    <div class="chart" data-testid="dur-chart">${durBars || "<span class='meta'>no data</span>"}</div>
    <h2>Flakiness board</h2>
    <div class="table-wrap">
      <table data-testid="flaky-table">
        <thead>
          <tr><th>Test</th><th>Runs</th><th>P/F</th><th>Pass%</th><th>Flake</th></tr>
        </thead>
        <tbody>${flaky || `<tr><td colspan="5">No flaky tests detected.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}
