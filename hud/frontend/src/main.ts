import "./style.css";
import { ensureCsrf, esc, fmtDur, getMeta, listRuns, type RunSummary } from "./api";
import { renderRun } from "./pages/run";
import { renderTest } from "./pages/test";
import { renderTrends } from "./pages/trends";
import { renderLive, startLive } from "./pages/live";
import { renderLaunch, wireLaunch } from "./pages/launch";
import { renderQuarantine, wireQuarantine } from "./pages/quarantine";
import { renderProfiles, wireProfiles } from "./pages/profiles";
import { renderPerf, wirePerf } from "./pages/perf";

const app = document.querySelector<HTMLDivElement>("#app")!;

let readOnly = false;
let smokeMode = false;
let staleApi = false;

function shell(active: string, body: string): string {
  const link = (href: string, label: string) =>
    `<a href="${href}" class="${active === label ? "active" : ""}">${label}</a>`;
  const control = readOnly
    ? ""
    : `${link("#/launch", "Launch")}
        ${link("#/quarantine", "Quarantine")}
        ${link("#/profiles", "Profiles")}`;
  const badges = [
    readOnly ? `<span class="badge warn" title="--read-only">RO</span>` : "",
    smokeMode
      ? `<span class="badge warn" title="Playwright smoke fixture — not real runs">SMOKE</span>`
      : "",
    staleApi
      ? `<span class="badge warn" title="Restart questline hud">STALE API</span>`
      : "",
  ]
    .filter(Boolean)
    .join(" ");
  const smokeBanner = smokeMode
    ? `<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)">
        <strong>SMOKE FIXTURE SERVER</strong> — fake launcher + seeded runs.
        For real Wire/mock runs stop this process and use
        <code>uv run questline hud --open</code> (port 8741).
      </div>`
    : "";
  const staleBanner = staleApi
    ? `<div class="empty" style="margin:0 0 0.75rem;border-color:var(--warn)" data-testid="stale-api">
        <strong>STALE HUD PROCESS</strong> — SPA is newer than the Python API
        (missing <code>/api/runs/…/test?id=</code>). Stop the old
        <code>questline hud</code> and run <code>uv run questline hud --open</code>
        again from the repo root, then hard-refresh.
      </div>`
    : "";
  return `
    <header class="topbar">
      <a class="brand" href="#/">Questline <span>HUD</span></a>
      <nav class="nav">
        ${link("#/", "Runs")}
        ${control}
        ${link("#/perf", "Perf")}
        ${link("#/trends", "Trends")}
        ${link("#/live", "Live")}
      </nav>
      ${badges}
    </header>
    <main class="main">${smokeBanner}${staleBanner}${body}</main>
  `;
}

function route(): { name: string; params: Record<string, string> } {
  const hash = location.hash.replace(/^#\/?/, "") || "";
  const parts = hash.split("/").filter(Boolean);
  // test_id is pytest nodeid and may contain '/' — take the remainder after /tests/
  if (parts[0] === "runs" && parts[1] && parts[2] === "tests" && parts.length >= 4) {
    const raw = parts.slice(3).join("/");
    let testId = raw;
    try {
      testId = decodeURIComponent(raw);
    } catch {
      /* keep raw */
    }
    return { name: "test", params: { runId: parts[1], testId } };
  }
  if (parts[0] === "runs" && parts[1]) {
    return { name: "run", params: { runId: parts[1] } };
  }
  if (parts[0] === "trends") return { name: "trends", params: {} };
  if (parts[0] === "live") return { name: "live", params: {} };
  if (parts[0] === "launch") return { name: "launch", params: {} };
  if (parts[0] === "quarantine") return { name: "quarantine", params: {} };
  if (parts[0] === "profiles") return { name: "profiles", params: {} };
  if (parts[0] === "perf") return { name: "perf", params: {} };
  return { name: "runs", params: {} };
}

function runsTable(runs: RunSummary[]): string {
  if (!runs.length) {
    return `<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Use <a href="#/launch">Launch</a> or run a suite with the questline plugin, then refresh.
    </div>`;
  }
  const rows = runs
    .map(
      (r) => `
    <tr data-testid="run-row" data-run-id="${esc(r.id)}">
      <td class="wrap"><a href="#/runs/${esc(r.id)}">${esc(r.id.slice(0, 8))}…</a></td>
      <td>${esc(r.profile)}</td>
      <td>${esc(r.driver ?? "—")}</td>
      <td>${esc(r.device ?? "—")}</td>
      <td><span class="badge ${esc(r.status)}">${esc(r.status)}</span></td>
      <td>${r.passed}/${r.total}</td>
      <td class="verdict-infra">${r.infra_failures}</td>
      <td class="verdict-test">${r.test_failures}</td>
      <td>${esc(fmtDur(r.duration_s))}</td>
      <td>${esc(r.started_at ?? "")}</td>
    </tr>`,
    )
    .join("");
  return `
    <div class="table-wrap">
      <table data-testid="runs-table">
        <thead>
          <tr>
            <th>Run</th><th>Profile</th><th>Driver</th><th>Device</th>
            <th>Status</th><th>Pass</th><th>Infra</th><th>Test</th>
            <th>Duration</th><th>Started</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

async function renderRuns(): Promise<string> {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const profile = params.get("profile") || "";
  const status = params.get("status") || "";
  const data = await listRuns({
    profile: profile || undefined,
    status: status || undefined,
  });
  return `
    <h1>Runs</h1>
    <div class="toolbar">
      <label>profile <input id="f-profile" value="${esc(profile)}" placeholder="any"/></label>
      <label>status
        <select id="f-status">
          <option value="">any</option>
          ${["passed", "failed", "running", "error"]
            .map(
              (s) =>
                `<option value="${s}" ${status === s ? "selected" : ""}>${s}</option>`,
            )
            .join("")}
        </select>
      </label>
      <button type="button" id="f-apply">Filter</button>
      ${readOnly ? "" : `<a class="btn" href="#/launch">Launch run</a>`}
    </div>
    ${runsTable(data.runs)}
  `;
}

async function paint(): Promise<void> {
  const r = route();
  try {
    let body = "";
    let active = "Runs";
    if (r.name === "run") {
      body = await renderRun(r.params.runId);
      active = "Runs";
    } else if (r.name === "test") {
      body = await renderTest(r.params.runId, r.params.testId);
      active = "Runs";
    } else if (r.name === "trends") {
      body = await renderTrends();
      active = "Trends";
    } else if (r.name === "live") {
      body = await renderLive();
      active = "Live";
    } else if (r.name === "launch") {
      body = await renderLaunch();
      active = "Launch";
    } else if (r.name === "quarantine") {
      body = await renderQuarantine();
      active = "Quarantine";
    } else if (r.name === "profiles") {
      body = await renderProfiles();
      active = "Profiles";
    } else if (r.name === "perf") {
      body = await renderPerf();
      active = "Perf";
    } else {
      body = await renderRuns();
      active = "Runs";
    }
    app.innerHTML = shell(active, body);
    wire(r.name);
  } catch (err) {
    app.innerHTML = shell(
      "Runs",
      `<div class="empty">Failed to load HUD: ${esc(String(err))}</div>`,
    );
  }
}

function wire(name: string): void {
  if (name === "runs") {
    document.getElementById("f-apply")?.addEventListener("click", () => {
      const profile = (document.getElementById("f-profile") as HTMLInputElement).value.trim();
      const status = (document.getElementById("f-status") as HTMLSelectElement).value;
      const q = new URLSearchParams();
      if (profile) q.set("profile", profile);
      if (status) q.set("status", status);
      const qs = q.toString();
      location.hash = qs ? `/?${qs}` : "/";
    });
  }
  if (name === "live") {
    const mount = document.getElementById("live-root");
    if (mount) {
      startLive(mount);
    }
  }
  if (name === "launch") wireLaunch();
  if (name === "quarantine") wireQuarantine();
  if (name === "profiles") wireProfiles();
  if (name === "perf") wirePerf();
}

async function boot(): Promise<void> {
  try {
    const meta = await getMeta();
    readOnly = !!meta.read_only;
    smokeMode = !!meta.smoke;
    staleApi = !meta.api?.test_by_query;
    if (!readOnly) await ensureCsrf();
  } catch {
    readOnly = false;
    smokeMode = false;
    staleApi = true;
  }
  await paint();
}

window.addEventListener("hashchange", () => {
  void paint();
});
void boot();
