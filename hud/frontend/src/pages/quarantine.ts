import {
  addQuarantine,
  auditQuarantine,
  ensureCsrf,
  esc,
  getMeta,
  listQuarantine,
  removeQuarantine,
} from "../api";

export async function renderQuarantine(): Promise<string> {
  await ensureCsrf();
  const meta = await getMeta();
  if (meta.read_only) {
    return `<h1>Quarantine</h1>
      <div class="empty">Read-only mode — quarantine management disabled.</div>`;
  }
  const data = await listQuarantine();
  const rows = (data.entries || [])
    .map(
      (e) => `<tr data-testid="quarantine-row">
        <td class="wrap">${esc(e.test_id)}</td>
        <td class="wrap">${esc(e.reason)}</td>
        <td>${esc(e.owner)}</td>
        <td>${esc(e.date)}</td>
        <td class="wrap">${esc(e.exit_criteria)}</td>
        <td>${esc(e.issue ?? "—")}</td>
        <td><button type="button" class="q-remove" data-id="${esc(e.test_id)}">Remove</button></td>
      </tr>`,
    )
    .join("");

  return `
    <h1>Quarantine</h1>
    <p class="meta">Ledger: <code>${esc(data.path)}</code> — same <code>QuarantineLedger</code> as CLI.</p>
    <div class="panel" data-testid="quarantine-add">
      <h2>Add</h2>
      <div class="toolbar">
        <label>test_id <input id="q-id" data-testid="q-id" placeholder="path::test" style="min-width:18rem"/></label>
        <label>owner <input id="q-owner" data-testid="q-owner"/></label>
      </div>
      <div class="toolbar">
        <label>reason <input id="q-reason" data-testid="q-reason" style="min-width:16rem"/></label>
        <label>exit <input id="q-exit" data-testid="q-exit" style="min-width:16rem"/></label>
        <label>issue <input id="q-issue"/></label>
      </div>
      <button type="button" id="q-add" data-testid="q-add">Add to ledger</button>
      <button type="button" id="q-audit" data-testid="q-audit">Limbo audit</button>
    </div>
    <pre class="log" id="q-msg" data-testid="q-msg"></pre>
    <div class="table-wrap">
      <table data-testid="quarantine-table">
        <thead>
          <tr><th>Test</th><th>Reason</th><th>Owner</th><th>Date</th><th>Exit</th><th>Issue</th><th></th></tr>
        </thead>
        <tbody>${rows || `<tr><td colspan="7">No quarantine entries.</td></tr>`}</tbody>
      </table>
    </div>
  `;
}

export function wireQuarantine(): void {
  const msg = document.getElementById("q-msg");
  document.getElementById("q-add")?.addEventListener("click", () => {
    void (async () => {
      try {
        await addQuarantine({
          test_id: (document.getElementById("q-id") as HTMLInputElement).value.trim(),
          owner: (document.getElementById("q-owner") as HTMLInputElement).value.trim(),
          reason: (document.getElementById("q-reason") as HTMLInputElement).value.trim(),
          exit_criteria: (document.getElementById("q-exit") as HTMLInputElement).value.trim(),
          issue:
            (document.getElementById("q-issue") as HTMLInputElement).value.trim() ||
            undefined,
        });
        location.reload();
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });

  document.getElementById("q-audit")?.addEventListener("click", () => {
    void (async () => {
      try {
        const report = await auditQuarantine({});
        if (msg) msg.textContent = report.summary;
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });

  document.querySelectorAll<HTMLButtonElement>(".q-remove").forEach((btn) => {
    btn.addEventListener("click", () => {
      void (async () => {
        const id = btn.dataset.id || "";
        try {
          await removeQuarantine(id);
          location.reload();
        } catch (err) {
          if (msg) msg.textContent = String(err);
        }
      })();
    });
  });
}
