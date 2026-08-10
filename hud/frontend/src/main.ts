import "./style.css";
import { esc, fmtDur, listRuns, type RunSummary } from "./api";
import { renderRun } from "./pages/run";
import { renderTest } from "./pages/test";
import { renderTrends } from "./pages/trends";
import { renderLive, startLive } from "./pages/live";

const app = document.querySelector<HTMLDivElement>("#app")!;

function shell(active: string, body: string): string {
  const link = (href: string, label: string) =>
    `<a href="${href}" class="${active === label ? "active" : ""}">${label}</a>`;
  return `
    <header class="topbar">
      <a class="brand" href="#/">Questline <span>HUD</span></a>
      <nav class="nav">
        ${link("#/", "Runs")}
        ${link("#/trends", "Trends")}
        ${link("#/live", "Live")}
      </nav>
    </header>
    <main class="main">${body}</main>
  `;
}

function route(): { name: string; params: Record<string, string> } {
  const hash = location.hash.replace(/^#\/?/, "") || "";
  const parts = hash.split("/").filter(Boolean);
  if (parts[0] === "runs" && parts[1] && parts[2] === "tests" && parts[3]) {
    return { name: "test", params: { runId: parts[1], testId: parts[3] } };
  }
  if (parts[0] === "runs" && parts[1]) {
    return { name: "run", params: { runId: parts[1] } };
  }
  if (parts[0] === "trends") return { name: "trends", params: {} };
  if (parts[0] === "live") return { name: "live", params: {} };
  return { name: "runs", params: {} };
}

function runsTable(runs: RunSummary[]): string {
  if (!runs.length) {
    return `<div class="empty" data-testid="empty-store">
      No runs in the store yet.<br/>
      Run a suite with the questline plugin, then refresh.
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
}

window.addEventListener("hashchange", () => {
  void paint();
});
void paint();
