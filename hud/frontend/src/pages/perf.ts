import { comparePerf, esc, getPerf, listRuns } from "../api";

function sparkline(
  points: Array<{ v?: number }>,
  color = "var(--accent)",
): string {
  const vals = points.map((p) => Number(p.v ?? 0));
  if (!vals.length) return `<span class="meta">no samples</span>`;
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = Math.max(1e-9, max - min);
  const w = 320;
  const h = 64;
  const coords = vals
    .map((v, i) => {
      const x = (i / Math.max(1, vals.length - 1)) * w;
      const y = h - ((v - min) / span) * (h - 4) - 2;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">
    <polyline fill="none" stroke="${color}" stroke-width="1.5" points="${coords}"/>
  </svg>`;
}

export async function renderPerf(): Promise<string> {
  const runs = await listRuns({});
  const opts = runs.runs
    .map((r) => `<option value="${esc(r.id)}">${esc(r.id.slice(0, 8))}… · ${esc(r.profile)}</option>`)
    .join("");
  const a = runs.runs[0]?.id || "";

  let seriesHtml = `<div class="empty">Pick a run to load perf series.</div>`;
  if (a) {
    const data = await getPerf(a);
    seriesHtml = renderSeries(a, data.series, data.summary);
  }

  return `
    <h1>Perf graphs</h1>
    <p class="meta">Same data as <code>questline perf report</code>, with overlays and compare.</p>
    <div class="toolbar">
      <label>run
        <select id="perf-run" data-testid="perf-run">${opts}</select>
      </label>
      <button type="button" id="perf-load" data-testid="perf-load">Load series</button>
    </div>
    <div id="perf-series" data-testid="perf-series">${seriesHtml}</div>
    <h2>Build-over-build compare</h2>
    <div class="toolbar">
      <label>A (baseline)
        <select id="perf-a" data-testid="perf-a">${opts}</select>
      </label>
      <label>B
        <select id="perf-b" data-testid="perf-b">${opts}</select>
      </label>
      <button type="button" id="perf-compare" data-testid="perf-compare">Compare</button>
    </div>
    <div id="perf-compare-out" data-testid="perf-compare-out"></div>
    <script>
      // defaults selected via DOM after paint
    </script>
  `;
}

function renderSeries(
  runId: string,
  series: Record<string, Array<{ t?: string; v?: number }>>,
  summary: Record<string, Record<string, number>>,
): string {
  const metrics = Object.keys(series);
  if (!metrics.length) {
    return `<div class="empty">No perf samples for ${esc(runId)}.</div>`;
  }
  return metrics
    .map((m) => {
      const stats = summary[m] || {};
      return `<div class="panel" data-testid="perf-metric">
        <h2>${esc(m)} <span class="meta">avg ${esc(stats.avg?.toFixed?.(2) ?? "—")} · n ${esc(stats.count ?? 0)}</span></h2>
        ${sparkline(series[m] || [])}
      </div>`;
    })
    .join("");
}

export function wirePerf(): void {
  const seriesRoot = document.getElementById("perf-series");
  const compareOut = document.getElementById("perf-compare-out");
  const runSel = document.getElementById("perf-run") as HTMLSelectElement | null;
  const aSel = document.getElementById("perf-a") as HTMLSelectElement | null;
  const bSel = document.getElementById("perf-b") as HTMLSelectElement | null;

  // Prefer first two distinct runs for compare defaults.
  if (aSel && bSel && bSel.options.length > 1) {
    bSel.selectedIndex = 1;
  }

  document.getElementById("perf-load")?.addEventListener("click", () => {
    void (async () => {
      const id = runSel?.value || "";
      if (!id || !seriesRoot) return;
      try {
        const data = await getPerf(id);
        seriesRoot.innerHTML = renderSeries(id, data.series, data.summary);
      } catch (err) {
        seriesRoot.textContent = String(err);
      }
    })();
  });

  document.getElementById("perf-compare")?.addEventListener("click", () => {
    void (async () => {
      const a = aSel?.value || "";
      const b = bSel?.value || "";
      if (!compareOut) return;
      try {
        const data = await comparePerf(a, b);
        const rows = data.deltas
          .map(
            (d) => `<tr>
              <td>${esc(d.metric)}</td>
              <td>${esc(d.a?.avg?.toFixed?.(2) ?? "—")}</td>
              <td>${esc(d.b?.avg?.toFixed?.(2) ?? "—")}</td>
              <td>${d.delta_avg == null ? "—" : esc(d.delta_avg.toFixed(2))}</td>
            </tr>`,
          )
          .join("");
        const overlay = Object.keys(data.series_a)
          .map((m) => {
            const aPts = data.series_a[m] || [];
            const bPts = data.series_b[m] || [];
            return `<div class="panel">
              <h2>${esc(m)} overlay</h2>
              <div class="toolbar">
                <span class="meta">A</span>${sparkline(aPts, "var(--accent)")}
                <span class="meta">B</span>${sparkline(bPts, "var(--ok)")}
              </div>
            </div>`;
          })
          .join("");
        compareOut.innerHTML = `
          <div class="table-wrap">
            <table data-testid="perf-delta-table">
              <thead><tr><th>Metric</th><th>A avg</th><th>B avg</th><th>Δ avg</th></tr></thead>
              <tbody>${rows || `<tr><td colspan="4">No metrics</td></tr>`}</tbody>
            </table>
          </div>
          ${overlay}`;
      } catch (err) {
        compareOut.textContent = String(err);
      }
    })();
  });
}
