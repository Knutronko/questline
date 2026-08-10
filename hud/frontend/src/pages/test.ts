import { artifactUrl, esc, fmtDur, getTest } from "../api";

export async function renderTest(runId: string, testId: string): Promise<string> {
  const data = await getTest(runId, testId);
  const t = data.test;
  const steps = data.steps
    .map((s) => {
      const status = String(s.status ?? "");
      return `<li data-testid="step-row">
        <span class="ts">${esc(s.started_at ?? "")}</span>
        <span class="badge ${esc(status)}">${esc(status)}</span>
        <span>${esc(s.name ?? "")}${s.error_message ? ` — ${esc(s.error_message)}` : ""}</span>
      </li>`;
    })
    .join("");

  const hist = (data.history || [])
    .map((h) => {
      const st = String(h.status ?? "");
      const dur = Number(h.duration_s ?? 0) || 1;
      const hgt = Math.max(4, Math.min(28, dur * 4));
      return `<i class="${esc(st)}" style="height:${hgt}px" title="${esc(st)}"></i>`;
    })
    .join("");

  const dp = data.death_point || {};
  const lastStarted = (dp.last_started_step || {}) as Record<string, unknown>;
  const health = (dp.driver_health || {}) as Record<string, unknown>;
  const verdictClass = t.verdict === "infra" ? "infra" : "";

  const arts = (data.artifacts || [])
    .map((a) => {
      const path = String(a.path ?? "");
      const kind = String(a.kind ?? "");
      const name = String(a.name ?? path);
      const url = artifactUrl(path);
      if (kind === "screenshot" || /\.(png|jpe?g|webp|gif)$/i.test(name)) {
        return `<div><a href="${esc(url)}" target="_blank" rel="noreferrer">
          <img src="${esc(url)}" alt="${esc(name)}"/><div>${esc(name)}</div></a></div>`;
      }
      return `<div><a href="${esc(url)}" target="_blank" rel="noreferrer">${esc(name)}</a>
        <div class="meta">${esc(kind)} · ${esc(a.size_bytes ?? "")} B</div></div>`;
    })
    .join("");

  return `
    <p class="meta">
      <a href="#/">Runs</a> /
      <a href="#/runs/${esc(runId)}">${esc(runId.slice(0, 8))}…</a>
    </p>
    <h1 data-testid="test-title">${esc(t.nodeid)}</h1>
    <div class="meta">
      status=<span class="badge ${esc(t.status)}">${esc(t.status)}</span> ·
      verdict=<span class="verdict-${esc(t.verdict ?? "")}">${esc(t.verdict ?? "—")}</span> ·
      duration=${esc(fmtDur(t.duration_s))}
    </div>

    <div class="panel death ${verdictClass}" data-testid="death-point">
      <h2>Death point</h2>
      <div>last started: <b>${esc(lastStarted.name ?? "—")}</b>
        @ ${esc(lastStarted.started_at ?? "")}</div>
      <div>error: ${esc(t.error_type ?? "")} — ${esc(t.error_message ?? "")}</div>
      <div>driver health: ${esc(JSON.stringify(health || {}))}</div>
    </div>

    <h2>History</h2>
    <div class="spark" data-testid="history-spark">${hist || "<span class='meta'>no history</span>"}</div>

    <h2>Step timeline</h2>
    <ul class="timeline" data-testid="step-timeline">${steps || "<li>No steps.</li>"}</ul>

    <h2>Artifacts</h2>
    <div class="art-grid" data-testid="artifacts">${arts || "<span class='meta'>none</span>"}</div>
  `;
}
