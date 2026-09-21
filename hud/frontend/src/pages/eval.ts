import {
  compareEvalRuns,
  esc,
  getMeta,
  listEvalRuns,
  runEval,
} from "../api";

function pct(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function num(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "—";
  return n.toFixed(3);
}

export async function renderEval(): Promise<string> {
  const data = await listEvalRuns();
  const runs = data.runs || [];
  const opts = runs
    .map((r) => `<option value="${esc(r.id)}">${esc(r.id)} · ${esc(r.provider || "—")}</option>`)
    .join("");
  const a = runs[1]?.id || runs[0]?.id || "";
  const b = runs[0]?.id || "";
  const rows = runs
    .map(
      (r) => `
    <tr data-testid="eval-row" data-eval-id="${esc(r.id)}">
      <td class="wrap"><code>${esc(r.id)}</code></td>
      <td>${esc(r.provider ?? "—")}</td>
      <td>${esc(r.prompt_version ?? "")}</td>
      <td>${esc(pct(r.diagnosis_accuracy))}</td>
      <td>${esc(pct(r.fix_correctness))}</td>
      <td>${esc(pct(r.false_green_rate))}</td>
      <td>${esc(num(r.iterations_avg))}</td>
      <td>${r.case_count ?? 0}</td>
      <td>${esc(r.created_at ?? "")}</td>
    </tr>`,
    )
    .join("");

  let canMutate = true;
  try {
    canMutate = !(await getMeta()).read_only;
  } catch {
    canMutate = true;
  }

  return `
    <h1>Eval harness</h1>
    <p class="meta">Golden MockDriver cases. Metrics are gate-owned — models do not invent green/red.</p>
    <div class="table-wrap">
      <table data-testid="eval-table">
        <thead>
          <tr>
            <th>Id</th><th>Provider</th><th>Prompt</th>
            <th>Diagnosis</th><th>Fix</th><th>False-green</th>
            <th>Iters</th><th>n</th><th>When</th>
          </tr>
        </thead>
        <tbody>${rows || `<tr><td colspan="9">No eval runs in this store.</td></tr>`}</tbody>
      </table>
    </div>
    <div class="toolbar">
      <label>A <select id="eval-a" data-testid="eval-a">${opts}</select></label>
      <label>B <select id="eval-b" data-testid="eval-b">${opts}</select></label>
      <button type="button" id="eval-compare" data-testid="eval-compare">Compare</button>
      ${canMutate ? `<button type="button" id="eval-run" data-testid="eval-run">Run fake eval</button>` : ""}
      <span id="eval-msg" class="meta" data-testid="eval-msg"></span>
    </div>
    <div id="eval-compare-out" data-testid="eval-compare-out"></div>
    <p class="meta">To write steps and generate a pytest file, open <a href="#/generate">Generate</a>.</p>
    <script type="application/json" id="eval-defaults">${JSON.stringify({ a, b })}</script>
  `;
}

export function wireEval(): void {
  const defaults = JSON.parse(
    document.getElementById("eval-defaults")?.textContent || "{}",
  ) as { a?: string; b?: string };
  const selA = document.getElementById("eval-a") as HTMLSelectElement | null;
  const selB = document.getElementById("eval-b") as HTMLSelectElement | null;
  if (selA && defaults.a) selA.value = defaults.a;
  if (selB && defaults.b) selB.value = defaults.b;

  document.getElementById("eval-compare")?.addEventListener("click", () => {
    void (async () => {
      const a = (document.getElementById("eval-a") as HTMLSelectElement).value;
      const b = (document.getElementById("eval-b") as HTMLSelectElement).value;
      const mount = document.getElementById("eval-compare-out");
      if (!mount || !a || !b) return;
      const data = await compareEvalRuns(a, b);
      const cmp = data.compare as {
        a?: { metrics?: Record<string, number | null> };
        b?: { metrics?: Record<string, number | null> };
        delta_b_minus_a?: Record<string, number | null>;
      };
      const keys = [
        "diagnosis_accuracy",
        "fix_correctness",
        "false_green_rate",
        "iterations_avg",
        "cost_usd",
      ];
      const rows = keys
        .map((k) => {
          const va = cmp.a?.metrics?.[k];
          const vb = cmp.b?.metrics?.[k];
          const d = cmp.delta_b_minus_a?.[k];
          return `<tr><td>${esc(k)}</td><td>${esc(num(va ?? null))}</td>
            <td>${esc(num(vb ?? null))}</td><td>${esc(num(d ?? null))}</td></tr>`;
        })
        .join("");
      mount.innerHTML = `
        <div class="table-wrap">
          <table data-testid="eval-delta-table">
            <thead><tr><th>Metric</th><th>A</th><th>B</th><th>B−A</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </div>`;
    })();
  });

  document.getElementById("eval-run")?.addEventListener("click", () => {
    const msg = document.getElementById("eval-msg");
    if (msg) msg.textContent = "running…";
    void (async () => {
      try {
        const res = await runEval({ provider: "fake", prompt_version: "v1" });
        if (msg) {
          msg.textContent = `ok ${res.run.id} false-green=${pct(res.run.false_green_rate)}`;
        }
        location.hash = "/eval";
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });
}
