import {
  artifactUrl,
  esc,
  fmtDur,
  getMeta,
  getTest,
  listAgentTasks,
  runDiagnose,
  runHeal,
  type AgentTask,
} from "../api";

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

  const failed = t.status === "failed" || t.status === "error";
  let canMutate = true;
  try {
    canMutate = !(await getMeta()).read_only;
  } catch {
    canMutate = true;
  }
  const locatorMiss = String(t.error_type ?? "").includes("ElementNotFound");
  let tasks: AgentTask[] = [];
  try {
    const listed = await listAgentTasks(runId);
    tasks = (listed.tasks || []).filter((x) => !x.test_id || x.test_id === testId);
  } catch {
    tasks = [];
  }

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

    ${
      failed && canMutate
        ? `<div class="toolbar" data-testid="agent-test-actions">
      <button type="button" id="diagnose-test" data-testid="diagnose-test">Diagnose this test</button>
      <button type="button" id="fix-test" data-testid="fix-test">Fix this test</button>
      ${
        locatorMiss
          ? `<button type="button" id="heal-test" data-testid="heal-test">Suggest locator</button>`
          : ""
      }
      <span id="diagnose-msg" class="meta" data-testid="diagnose-msg"></span>
    </div>
    <div id="diagnose-result" data-testid="diagnose-result">${renderTaskList(tasks)}</div>
    <script type="application/json" id="test-agent-ctx">${JSON.stringify({ runId, testId, locatorMiss })}</script>`
        : ""
    }

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

export function wireTest(): void {
  const ctxEl = document.getElementById("test-agent-ctx");
  let runId = "";
  let testId = "";
  try {
    const ctx = JSON.parse(ctxEl?.textContent || "{}") as {
      runId?: string;
      testId?: string;
    };
    runId = ctx.runId || "";
    testId = ctx.testId || "";
  } catch {
    return;
  }
  const msg = () => document.getElementById("diagnose-msg");
  const mount = () => document.getElementById("diagnose-result");
  document.getElementById("diagnose-test")?.addEventListener("click", () => {
    void runAction("diagnose", runId, testId, msg(), mount());
  });
  document.getElementById("fix-test")?.addEventListener("click", () => {
    if (!window.confirm("Fix mode writes files under the project jail and re-runs the test. Continue?")) {
      return;
    }
    void runAction("fix", runId, testId, msg(), mount());
  });
  document.getElementById("heal-test")?.addEventListener("click", () => {
    void runAction("heal", runId, testId, msg(), mount());
  });
}

async function runAction(
  kind: "diagnose" | "fix" | "heal",
  runId: string,
  testId: string,
  msg: HTMLElement | null,
  mount: HTMLElement | null,
): Promise<void> {
  if (!runId || !testId) return;
  if (msg) msg.textContent = "running…";
  try {
    const res =
      kind === "heal"
        ? await runHeal({ run_id: runId, test_id: testId })
        : await runDiagnose({ run_id: runId, test_id: testId, fix: kind === "fix" });
    if (msg) msg.textContent = `status=${res.task.status} verdict=${res.task.verdict}`;
    if (mount) mount.innerHTML = renderTaskPanel(res.task);
  } catch (err) {
    if (msg) msg.textContent = String(err);
  }
}

function renderTaskList(tasks: AgentTask[]): string {
  if (!tasks.length) return "";
  return tasks.map(renderTaskPanel).join("");
}

function renderTaskPanel(task: AgentTask): string {
  const sug = task.suggestion || {};
  const diff = typeof sug.yaml_diff === "string" ? sug.yaml_diff : "";
  const gate = task.gate ? `gate accepted=${esc(String(task.gate.accepted ?? ""))}` : "";
  return `
    <div class="panel" data-testid="agent-task" data-task-kind="${esc(task.kind ?? "")}">
      <div class="meta">kind=${esc(task.kind ?? "")} · verdict=${esc(task.verdict ?? "")}
        · cause=${esc(task.cause ?? "")} ${gate}</div>
      <p>${esc(task.summary ?? "")}</p>
      ${diff ? `<pre data-testid="heal-diff">${esc(diff)}</pre>` : ""}
    </div>`;
}
