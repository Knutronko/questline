import {
  esc,
  getMeta,
  launchRun,
  listDevices,
  listGenerateTasks,
  runGenerate,
  type AgentTask,
} from "../api";

const LAST_GEN_KEY = "ql-last-generated";

const DEFAULT_SPEC_MOCK = `When the player taps Play, the HUD is visible.
Coins start at 100.
expect: green`;

const DEFAULT_SPEC_SUITE = `Ping the game. The Ping hook returns pong.
expect: green`;

type GateInfo = {
  nodeid?: string;
  stdout_tail?: string;
  accepted?: boolean;
  mode?: string;
  mock_driver?: boolean;
  reason?: string;
};

function gateLine(task: AgentTask): string {
  const gate = (task.gate || {}) as {
    executed?: boolean;
    accepted?: boolean;
    expected?: string;
    green?: boolean;
    reason?: string;
    nodeid?: string;
    mode?: string;
    mock_driver?: boolean;
  };
  const bits = [
    `verdict=${task.verdict ?? "—"}`,
    `mode=${gate.mode ?? "—"}`,
    `executed=${String(gate.executed ?? false)}`,
    `accepted=${String(gate.accepted ?? false)}`,
    gate.mock_driver ? "mock_driver=true" : "",
    gate.expected ? `expected=${gate.expected}` : "",
    gate.green != null ? `green=${String(gate.green)}` : "",
    gate.reason ? `reason=${gate.reason}` : "",
  ].filter(Boolean);
  return bits.join(" · ");
}

function isRateLimited(task: AgentTask): boolean {
  const gate = (task.gate || {}) as GateInfo;
  const blob = `${task.summary || ""} ${gate.reason || ""}`;
  return (
    gate.reason === "rate_limited" ||
    /\b429\b/.test(blob) ||
    /rate limit/i.test(blob)
  );
}

function resultCard(task: AgentTask, smoke: boolean): string {
  const gate = (task.gate || {}) as GateInfo;
  const stdout = String(gate.stdout_tail || "").trim();
  const nodeid = String(gate.nodeid || "");
  const mock = !!gate.mock_driver;
  const showLaunch = !smoke && !!gate.accepted && !!nodeid && !mock;
  const launch = showLaunch
    ? `<div class="toolbar" data-testid="gen-launch">
        <button type="button" id="gen-launch-editor" data-testid="gen-launch-editor">Launch Editor</button>
        <button type="button" id="gen-launch-android" data-testid="gen-launch-android">Launch Android</button>
        <label>device
          <select id="gen-device" data-testid="gen-device">
            <option value="">(auto / Editor OK)</option>
          </select>
        </label>
        <span class="meta">Unity Play + Wire, or APK + adb, must already be up.</span>
        <span id="gen-launch-msg" class="meta" data-testid="gen-launch-msg"></span>
      </div>`
    : mock && !smoke
      ? `<p class="meta" data-testid="gen-mock-warn">This file is MockDriver (Demo). Unity will not move. Uncheck Demo, set GROQ_API_KEY on this HUD process, and Generate again with steps that match existing pages/hooks.</p>`
      : "";
  const rateHint = isRateLimited(task)
    ? `<p class="empty" data-testid="gen-429">Groq rate limit (HTTP 429). Wait about 20 seconds, then Generate again. Optional: run Ollama locally as fallback.</p>`
    : "";
  return `
    <div class="panel" data-testid="gen-result">
      <p class="meta" data-testid="gen-gate">${esc(gateLine(task))}</p>
      <p class="meta">task <code>${esc(task.id)}</code>
        ${nodeid ? ` · file <code data-testid="gen-nodeid">${esc(nodeid)}</code>` : ""}</p>
      ${rateHint}
      <p>${esc(task.summary || "")}</p>
      ${
        gate.mode === "collect" && gate.accepted && !mock
          ? `<p class="meta">Collect gate passed — not a live Unity/device run.</p>`
          : ""
      }
      ${launch}
      ${
        stdout
          ? `<pre class="log" data-testid="gen-stdout">${esc(stdout)}</pre>`
          : ""
      }
    </div>`;
}

function taskRows(tasks: AgentTask[]): string {
  if (!tasks.length) {
    return `<p class="meta" data-testid="gen-empty">No generate tasks in this store yet.</p>`;
  }
  const rows = tasks
    .map(
      (t) => `
    <tr data-testid="gen-row" data-task-id="${esc(t.id)}">
      <td class="wrap"><code>${esc(t.id)}</code></td>
      <td><span class="badge ${esc(t.verdict || "")}">${esc(t.verdict || "—")}</span></td>
      <td>${esc(String((t.gate as { accepted?: boolean } | null)?.accepted ?? "—"))}</td>
      <td>${esc(t.created_at ?? "")}</td>
    </tr>`,
    )
    .join("");
  return `
    <div class="table-wrap">
      <table data-testid="gen-table">
        <thead><tr><th>Task</th><th>Verdict</th><th>Accepted</th><th>When</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

async function fillDevices(): Promise<void> {
  const sel = document.getElementById("gen-device") as HTMLSelectElement | null;
  if (!sel) return;
  try {
    const data = await listDevices();
    const current = sel.value;
    sel.innerHTML = [
      `<option value="">(auto / Editor OK)</option>`,
      ...(data.devices || []).map(
        (d) =>
          `<option value="${esc(d.id)}">${esc(d.id)} · ${esc(d.platform)}</option>`,
      ),
    ].join("");
    if (current) sel.value = current;
  } catch {
    /* picker stays empty */
  }
}

function wireLaunchButtons(nodeid: string): void {
  const start = (profile: string, live: boolean) => {
    void (async () => {
      const device = (document.getElementById("gen-device") as HTMLSelectElement | null)
        ?.value;
      const launchMsg = document.getElementById("gen-launch-msg");
      const msg = document.getElementById("gen-msg");
      const line = `launching ${profile}…`;
      if (launchMsg) launchMsg.textContent = line;
      if (msg) msg.textContent = line;
      const editorBtn = document.getElementById(
        "gen-launch-editor",
      ) as HTMLButtonElement | null;
      const androidBtn = document.getElementById(
        "gen-launch-android",
      ) as HTMLButtonElement | null;
      if (editorBtn) editorBtn.disabled = true;
      if (androidBtn) androidBtn.disabled = true;
      try {
        await launchRun({
          profile,
          tests: [nodeid],
          device_serial: device || undefined,
          config: "questline.toml",
          live_target: live,
          reporters: ["console"],
        });
        location.hash = "/live";
      } catch (err) {
        const text = String(err);
        if (launchMsg) launchMsg.textContent = text;
        if (msg) msg.textContent = text;
        if (editorBtn) editorBtn.disabled = false;
        if (androidBtn) androidBtn.disabled = false;
      }
    })();
  };
  document.getElementById("gen-launch-editor")?.addEventListener("click", () => {
    start("editor", true);
  });
  document.getElementById("gen-launch-android")?.addEventListener("click", () => {
    start("android_local", true);
  });
  void fillDevices();
}

export async function renderGenerate(): Promise<string> {
  let canMutate = true;
  let smoke = false;
  let dest = "generated-tests";
  let hasPages = false;
  let hasLlm = false;
  try {
    const meta = await getMeta();
    canMutate = !meta.read_only;
    smoke = !!meta.smoke;
    dest = meta.default_generate_dest || dest;
    hasPages = !!meta.has_pages;
    hasLlm = !!meta.has_llm;
  } catch {
    canMutate = true;
  }
  const listed = await listGenerateTasks().catch(() => ({
    tasks: [] as AgentTask[],
    empty: true,
  }));
  const demoHint = smoke
    ? "SMOKE writes a canned Play→HUD MockDriver test. Launch Editor/Android is hidden here (fake launcher)."
    : "Uncheck Demo to send your steps to Groq/Ollama. Each Generate writes a new test_gen_*.py — it will not launch an old suite file. The collect gate does not start Unity — use Launch Editor / Android after. Demo = canned MockDriver (Unity will not move). HTTP 429 = Groq rate limit: wait ~20s and Generate again (or start Ollama).";
  const llmWarn =
    !smoke && !hasLlm
      ? `<p class="empty" data-testid="gen-no-llm">No live LLM in this HUD process. Set <code>GROQ_API_KEY</code> (or run Ollama with an <code>ai_ollama</code> profile) and restart <code>questline hud</code>. Without that, Generate with Demo unchecked returns 400 — it will not silently write MockDriver.</p>`
      : "";
  const spec = hasPages && !smoke ? DEFAULT_SPEC_SUITE : DEFAULT_SPEC_MOCK;

  return `
    <h1>Generate tests</h1>
    <p class="meta">Write the steps. The agent writes a pytest using pages/locators under this HUD project root. Models do not invent green/red.</p>
    <p class="meta">${esc(demoHint)} Eval scores live on <a href="#/eval">Eval</a>.</p>
    ${llmWarn}
    ${
      canMutate
        ? `<form id="gen-form" data-testid="gen-form" class="panel">
      <label>Steps / spec
        <textarea id="gen-spec" data-testid="gen-spec" rows="8">${esc(spec)}</textarea>
      </label>
      <div class="toolbar">
        <label>dest <input id="gen-dest" data-testid="gen-dest" value="${esc(dest)}"/></label>
        <label class="check">
          <input type="checkbox" id="gen-demo" data-testid="gen-demo" ${smoke ? "checked" : ""}/>
          Demo (canned MockDriver)
        </label>
        <button type="button" id="gen-run" data-testid="gen-run">Generate</button>
        <span id="gen-msg" class="meta" data-testid="gen-msg"></span>
      </div>
    </form>
    <div id="gen-out" data-testid="gen-out"></div>`
        : `<p class="empty">Read-only HUD — Generate is disabled.</p>`
    }
    <h2>Recent</h2>
    ${taskRows(listed.tasks || [])}
  `;
}

export function wireGenerate(): void {
  document.getElementById("gen-run")?.addEventListener("click", () => {
    const spec = (document.getElementById("gen-spec") as HTMLTextAreaElement)?.value || "";
    const dest =
      (document.getElementById("gen-dest") as HTMLInputElement)?.value.trim() ||
      "generated-tests";
    const demo = (document.getElementById("gen-demo") as HTMLInputElement)?.checked ?? false;
    const msg = document.getElementById("gen-msg");
    const out = document.getElementById("gen-out");
    if (msg) msg.textContent = "generating…";
    void (async () => {
      let smoke = false;
      try {
        smoke = !!(await getMeta()).smoke;
      } catch {
        smoke = false;
      }
      try {
        const res = await runGenerate({ spec, dest, demo });
        if (msg) msg.textContent = gateLine(res.task);
        const gate = (res.task.gate || {}) as GateInfo;
        const nodeid = String(gate.nodeid || "");
        if (nodeid && !gate.mock_driver) {
          try {
            sessionStorage.setItem(LAST_GEN_KEY, nodeid);
          } catch {
            /* ignore */
          }
        }
        if (out) out.innerHTML = resultCard(res.task, smoke);
        if (nodeid && !gate.mock_driver) wireLaunchButtons(nodeid);
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });
}
