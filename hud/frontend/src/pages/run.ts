import {
  esc,
  fmtDur,
  getMeta,
  getRun,
  listAgentTasks,
  runTriage,
  type AgentTask,
} from "../api";

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

  const aiCalls = data.ai_calls || [];
  const aiRows =
    aiCalls
      .map(
        (c) => `
    <tr data-testid="ai-call-row">
      <td>${esc(c.provider ?? "—")}</td>
      <td class="wrap">${esc(c.model ?? "—")}</td>
      <td>${esc(c.tokens_in ?? 0)}</td>
      <td>${esc(c.tokens_out ?? 0)}</td>
      <td>${esc(fmtUsd(c.cost))}</td>
      <td>${esc(c.outcome ?? "—")}</td>
      <td class="wrap">${esc(c.purpose ?? "")}</td>
    </tr>`,
      )
      .join("") || `<tr><td colspan="7">No AI calls for this run.</td></tr>`;

  const failed = data.tests.some((t) => t.status === "failed" || t.status === "error");
  let canMutate = true;
  try {
    canMutate = !(await getMeta()).read_only;
  } catch {
    canMutate = true;
  }
  let tasks: AgentTask[] = [];
  try {
    const listed = await listAgentTasks(runId);
    tasks = listed.tasks || [];
  } catch {
    tasks = [];
  }

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
    ${
      failed && canMutate
        ? `<div class="toolbar" data-testid="agent-run-actions">
      <button type="button" id="triage-run" data-testid="triage-run">Triage this run</button>
      <span id="triage-msg" class="meta" data-testid="triage-msg"></span>
    </div>
    <div id="triage-result" data-testid="triage-result">${renderTaskList(tasks)}</div>
    <script type="application/json" id="run-agent-ctx">${JSON.stringify({ runId })}</script>`
        : ""
    }
    <h2>AI calls</h2>
    <div class="meta">total_usd=${esc(fmtUsd(data.ai_cost_total))}</div>
    <div class="table-wrap">
      <table data-testid="ai-calls-table">
        <thead>
          <tr>
            <th>Provider</th><th>Model</th><th>In</th><th>Out</th>
            <th>Cost</th><th>Outcome</th><th>Purpose</th>
          </tr>
        </thead>
        <tbody>${aiRows}</tbody>
      </table>
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

export function wireRun(): void {
  const btn = document.getElementById("triage-run");
  btn?.addEventListener("click", () => {
    void (async () => {
      const msg = document.getElementById("triage-msg");
      const mount = document.getElementById("triage-result");
      const raw = document.getElementById("run-agent-ctx")?.textContent;
      let runId = "";
      try {
        runId = String((JSON.parse(raw || "{}") as { runId?: string }).runId || "");
      } catch {
        /* ignore */
      }
      if (!runId) return;
      if (msg) msg.textContent = "running…";
      try {
        const res = await runTriage({ run_id: runId });
        if (msg) msg.textContent = `status=${res.task.status} verdict=${res.task.verdict}`;
        if (mount) mount.innerHTML = renderTaskPanel(res.task);
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });
}

function renderTaskList(tasks: AgentTask[]): string {
  if (!tasks.length) return `<p class="meta">No agent tasks yet.</p>`;
  return tasks.map(renderTaskPanel).join("");
}

function renderTaskPanel(task: AgentTask): string {
  const clusters = (task.clusters || [])
    .map((c) => {
      const bucket = String(c.bucket ?? c.key ?? "");
      const err = String(c.error_type ?? "");
      const n = Array.isArray(c.test_ids) ? c.test_ids.length : "";
      const hypo = String(c.hypothesis ?? c.signature ?? "");
      return `<li>${esc(bucket)} · ${esc(err)} x${esc(n)} — ${esc(hypo)}</li>`;
    })
    .join("");
  return `
    <div class="panel" data-testid="agent-task" data-task-kind="${esc(task.kind ?? "")}">
      <div class="meta">kind=${esc(task.kind ?? "")} · verdict=${esc(task.verdict ?? "")}
        · cause=${esc(task.cause ?? "")} · status=${esc(task.status ?? "")}</div>
      <p>${esc(task.summary ?? "")}</p>
      ${clusters ? `<ul data-testid="triage-clusters">${clusters}</ul>` : ""}
    </div>`;
}

function fmtUsd(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "0.000000";
  return n.toFixed(6);
}
