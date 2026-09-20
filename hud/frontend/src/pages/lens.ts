import {
  esc,
  getAgentTurn,
  getLensDiff,
  getMeta,
  getTelemetrySession,
  listAgentTurns,
  listLensSnapshots,
  listProfiles,
  listTelemetrySessions,
  runBalanceAgent,
  type AgentTurn,
  type LensDiffEntry,
  type LensImplications,
  type TelSession,
} from "../api";

function lensNav(active: string): string {
  const link = (href: string, label: string) =>
    `<a href="${href}" class="${active === label ? "active" : ""}">${label}</a>`;
  return `<div class="subnav" data-testid="lens-nav">
    ${link("#/lens", "Snapshots")}
    ${link("#/lens/diff", "Diff")}
    ${link("#/lens/sessions", "Sessions")}
    ${link("#/lens/turns", "Agent")}
  </div>`;
}

export async function renderLensHome(): Promise<string> {
  const data = await listLensSnapshots();
  const snaps = data.snapshots || [];
  const opts = snaps
    .map((s) => `<option value="${esc(s.id)}">${esc(s.id)} · ${esc(s.game_version)}</option>`)
    .join("");
  const a = snaps[1]?.id || snaps[0]?.id || "";
  const b = snaps[0]?.id || "";
  const rows = snaps
    .map(
      (s) => `
    <tr data-testid="lens-snap-row" data-snap-id="${esc(s.id)}">
      <td class="wrap"><code>${esc(s.id)}</code></td>
      <td>${esc(s.game_version)}</td>
      <td>${esc(s.feature_id ?? "—")}</td>
      <td>${esc(s.created_at ?? "")}</td>
    </tr>`,
    )
    .join("");
  return `
    <h1>GameLens</h1>
    ${lensNav("Snapshots")}
    <p class="meta">Config truth from <code>balance_snapshots</code>. AI never invents green/red.</p>
    <div class="toolbar">
      <label>A <select id="lens-a" data-testid="lens-a">${opts}</select></label>
      <label>B <select id="lens-b" data-testid="lens-b">${opts}</select></label>
      <button type="button" id="lens-open-diff" data-testid="lens-open-diff">Open typed diff</button>
    </div>
    <div class="table-wrap">
      <table data-testid="lens-snapshots">
        <thead><tr><th>Id</th><th>Version</th><th>Feature</th><th>Created</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4">No snapshots in this store.</td></tr>`}</tbody>
      </table>
    </div>
    <script type="application/json" id="lens-defaults">${JSON.stringify({ a, b })}</script>
  `;
}

export async function renderLensDiff(): Promise<string> {
  const snaps = (await listLensSnapshots()).snapshots || [];
  const q = new URLSearchParams(location.hash.split("?")[1] || "");
  const a = q.get("a") || snaps[1]?.id || snaps[0]?.id || "";
  const b = q.get("b") || snaps[0]?.id || "";
  if (!a || !b) {
    return `
      <h1>Typed diff</h1>
      ${lensNav("Diff")}
      <div class="empty" data-testid="lens-diff-empty">Pick two snapshots on GameLens.</div>`;
  }
  const data = await getLensDiff(a, b);
  const entries = data.diff.entries || [];
  const grouped = data.diff.by_system || {};
  const systems = Object.keys(grouped).sort();
  const blocks = systems
    .map((sys) => {
      const lines = (grouped[sys] || [])
        .map((e) => `<li data-testid="lens-diff-entry">${esc(formatEntry(e))}</li>`)
        .join("");
      return `<div class="panel"><h3>[${esc(sys)}]</h3><ul>${lines}</ul></div>`;
    })
    .join("");
  const impl = data.implications;
  let profiles: string[] = [];
  try {
    const meta = await getMeta();
    if (!meta.read_only) {
      profiles = (await listProfiles()).profiles || [];
    }
  } catch {
    profiles = [];
  }
  const aiOpts = profiles
    .filter((p) => p.startsWith("ai_"))
    .concat(profiles.filter((p) => !p.startsWith("ai_")))
    .map((p) => {
      const sel = p === "ai_groq" ? "selected" : "";
      return `<option value="${esc(p)}" ${sel}>${esc(p)}</option>`;
    })
    .join("");
  return `
    <h1>Typed diff</h1>
    ${lensNav("Diff")}
    <p class="meta" data-testid="lens-diff-meta">
      ${esc(data.diff.snapshot_id_a || a)} → ${esc(data.diff.snapshot_id_b || b)}
      · ${entries.length} entries · framing vs measured stay separate
    </p>
    ${blocks || `<div class="empty">(no differences)</div>`}
    ${renderImplications(impl)}
    <h2>Ask balance agent</h2>
    <p class="meta">Retune <em>priorities</em> only — model reasoning, never SO writes or green/red.</p>
    <div class="panel" data-testid="lens-agent-form">
      <label class="block">profile
        <select id="agent-profile" data-testid="agent-profile">${aiOpts || `<option value="ai_groq">ai_groq</option>`}</select>
      </label>
      <label class="block">question
        <textarea id="agent-q" data-testid="agent-q" rows="3">What should a human look at for a retune?</textarea>
      </label>
      <button type="button" id="agent-run" data-testid="agent-run">Ask</button>
      <div id="agent-msg" class="meta" data-testid="agent-msg"></div>
    </div>
    <div id="agent-result"></div>
    <script type="application/json" id="lens-pair">${JSON.stringify({ a, b })}</script>
  `;
}

export async function renderLensSessions(): Promise<string> {
  const data = await listTelemetrySessions();
  const rows = (data.sessions || [])
    .map(
      (s) => `
    <tr data-testid="tel-session-row" data-session-id="${esc(s.id)}">
      <td class="wrap"><a href="#/lens/sessions/${encodeURIComponent(s.id)}">${esc(s.id)}</a></td>
      <td>${esc(s.outcome ?? "—")}</td>
      <td class="wrap">${esc(s.config_snapshot_id ?? "—")}</td>
      <td>${esc(s.policy_id ?? "—")}</td>
      <td>${esc(s.seed ?? "—")}</td>
      <td class="wrap">${esc((s.notes || []).join("; "))}</td>
    </tr>`,
    )
    .join("");
  return `
    <h1>Telemetry sessions</h1>
    ${lensNav("Sessions")}
    <p class="meta"><code>outcome=lose</code> is measured play, not a bot/framework fail. <code>snap-unset</code> is a join gap.</p>
    <div class="table-wrap">
      <table data-testid="tel-sessions">
        <thead>
          <tr><th>Id</th><th>Outcome</th><th>Snapshot</th><th>Policy</th><th>Seed</th><th>Notes</th></tr>
        </thead>
        <tbody>${rows || `<tr><td colspan="6">No telemetry sessions.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

export async function renderLensSession(id: string): Promise<string> {
  const data = await getTelemetrySession(id);
  const s = data.session;
  return `
    <p class="meta"><a href="#/lens/sessions">← Sessions</a> · ${esc(s.id)}</p>
    <h1>Session</h1>
    ${lensNav("Sessions")}
    ${renderSessionBody(s)}
  `;
}

export async function renderLensTurns(): Promise<string> {
  const data = await listAgentTurns();
  const rows = (data.turns || [])
    .map(
      (t) => `
    <tr data-testid="agent-turn-row" data-turn-id="${esc(t.id)}">
      <td class="wrap"><a href="#/lens/turns/${encodeURIComponent(t.id)}">${esc(t.id)}</a></td>
      <td>${esc(t.status ?? "")}</td>
      <td>${esc(t.framing ?? "")}</td>
      <td class="wrap">${esc(t.question ?? "")}</td>
      <td>${esc(t.created_at ?? "")}</td>
    </tr>`,
    )
    .join("");
  return `
    <h1>Balance agent</h1>
    ${lensNav("Agent")}
    <p class="meta">Persisted turns. Numbers in citations are measured; priorities are model reasoning.</p>
    <div class="table-wrap">
      <table data-testid="agent-turns">
        <thead><tr><th>Id</th><th>Status</th><th>Framing</th><th>Question</th><th>Created</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5">No agent turns yet. Ask from a typed diff.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

export async function renderLensTurn(id: string): Promise<string> {
  const data = await getAgentTurn(id);
  return `
    <p class="meta"><a href="#/lens/turns">← Agent</a> · ${esc(id)}</p>
    <h1>Agent turn</h1>
    ${lensNav("Agent")}
    ${renderTurn(data.turn)}
  `;
}

export function wireLensHome(): void {
  const btn = document.getElementById("lens-open-diff");
  btn?.addEventListener("click", () => {
    const a = (document.getElementById("lens-a") as HTMLSelectElement | null)?.value;
    const b = (document.getElementById("lens-b") as HTMLSelectElement | null)?.value;
    if (!a || !b) return;
    location.hash = `/lens/diff?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`;
  });
  const raw = document.getElementById("lens-defaults")?.textContent;
  if (raw) {
    try {
      const d = JSON.parse(raw) as { a?: string; b?: string };
      const sa = document.getElementById("lens-a") as HTMLSelectElement | null;
      const sb = document.getElementById("lens-b") as HTMLSelectElement | null;
      if (sa && d.a) sa.value = d.a;
      if (sb && d.b) sb.value = d.b;
    } catch {
      /* ignore */
    }
  }
}

export function wireLensDiff(): void {
  const btn = document.getElementById("agent-run");
  btn?.addEventListener("click", () => {
    void (async () => {
      const msg = document.getElementById("agent-msg");
      const mount = document.getElementById("agent-result");
      const raw = document.getElementById("lens-pair")?.textContent;
      let a = "";
      let b = "";
      try {
        const pair = JSON.parse(raw || "{}") as { a?: string; b?: string };
        a = pair.a || "";
        b = pair.b || "";
      } catch {
        /* ignore */
      }
      const question = (document.getElementById("agent-q") as HTMLTextAreaElement | null)?.value;
      const profile = (document.getElementById("agent-profile") as HTMLSelectElement | null)?.value;
      if (msg) msg.textContent = "running…";
      try {
        const res = await runBalanceAgent({
          snapshot_a: a,
          snapshot_b: b,
          question: question || undefined,
          profile: profile || undefined,
        });
        if (msg) msg.textContent = `status=${res.turn.status}`;
        if (mount) mount.innerHTML = renderTurn(res.turn);
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });
}

function renderImplications(impl: LensImplications | null): string {
  if (!impl) {
    return `<div class="empty" data-testid="lens-impl-empty">No persisted implications for this pair.</div>`;
  }
  const gaps = (impl.gaps || []).map((g) => `<li>${esc(g)}</li>`).join("");
  return `
    <h2>Implications</h2>
    <div class="panel" data-testid="lens-implications">
      <div class="meta">status=${esc(impl.status ?? "")} · framing=${esc(impl.framing ?? "")}
        ${impl.pending ? ` · pending=${esc(impl.pending)}` : ""}</div>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="lens-gaps">${gaps || "<li>(none)</li>"}</ul>
      <h3>Model reasoning</h3>
      <div data-testid="lens-impl-summary">${esc(impl.summary ?? "")}</div>
      <h3>Measured</h3>
      <pre class="pre-json" data-testid="lens-measured">${esc(JSON.stringify(impl.measured ?? {}, null, 2))}</pre>
    </div>`;
}

function renderSessionBody(s: TelSession): string {
  const notes = (s.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");
  return `
    <div class="panel" data-testid="tel-session-detail">
      <div class="meta">outcome=${esc(s.outcome ?? "—")} · snapshot=${esc(s.config_snapshot_id ?? "—")}
        · policy=${esc(s.policy_id ?? "—")} · seed=${esc(s.seed ?? "—")}</div>
      <h3>Notes</h3>
      <ul data-testid="tel-session-notes">${notes || "<li>(none)</li>"}</ul>
      <h3>Summary (measured)</h3>
      <pre class="pre-json">${esc(JSON.stringify(s.summary ?? {}, null, 2))}</pre>
    </div>`;
}

function renderTurn(t: AgentTurn): string {
  const pri = (t.priorities || []).map((p) => `<li>${esc(p)}</li>`).join("");
  const gaps = (t.gaps || []).map((g) => `<li>${esc(g)}</li>`).join("");
  const cost = t.ai_cost_total != null ? String(t.ai_cost_total) : "—";
  return `
    <div class="panel" data-testid="agent-turn">
      <div class="meta">status=${esc(t.status ?? "")} · framing=${esc(t.framing ?? "")}
        · cost_usd=${esc(cost)}${t.pending ? ` · pending=${esc(t.pending)}` : ""}</div>
      <h3>Priorities (model reasoning)</h3>
      <ul data-testid="agent-priorities">${pri || "<li>(none)</li>"}</ul>
      <h3>Gaps</h3>
      <ul class="gap-list" data-testid="agent-gaps">${gaps || "<li>(none)</li>"}</ul>
      <h3>Measured citations</h3>
      <pre class="pre-json" data-testid="agent-measured">${esc(JSON.stringify(t.citations ?? {}, null, 2))}</pre>
    </div>`;
}

function formatEntry(e: LensDiffEntry): string {
  if (e.kind === "added_entity") return `+ entity ${e.entity_id}`;
  if (e.kind === "removed_entity") return `- entity ${e.entity_id}`;
  const path = e.path || "?";
  if (e.delta != null) {
    return `~ ${e.entity_id}.${path}: ${e.before} -> ${e.after} (delta ${e.delta})`;
  }
  return `~ ${e.entity_id}.${path}: ${JSON.stringify(e.before)} -> ${JSON.stringify(e.after)}`;
}
