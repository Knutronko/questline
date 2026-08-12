import {
  ensureCsrf,
  esc,
  getMeta,
  getProfile,
  listProfiles,
  saveProfile,
  validateProfile,
} from "../api";

export async function renderProfiles(): Promise<string> {
  await ensureCsrf();
  const meta = await getMeta();
  if (meta.read_only) {
    return `<h1>Profiles</h1>
      <div class="empty">Read-only mode — profile editor disabled.</div>`;
  }
  const { profiles, path } = await listProfiles();
  const opts = profiles
    .map((p) => `<option value="${esc(p)}">${esc(p)}</option>`)
    .join("");
  const first = profiles[0] || "";
  let fieldsJson = "{}";
  let secrets = "";
  if (first) {
    const p = await getProfile(first);
    fieldsJson = JSON.stringify(p.fields, null, 2);
    secrets = (p.secret_env_names || []).map((s) => `<code>${esc(s)}</code>`).join(" ");
  }
  return `
    <h1>Profile editor</h1>
    <p class="meta">Config: <code>${esc(path)}</code>. Secrets are env names only — never values.</p>
    <div class="toolbar">
      <label>profile
        <select id="prof-name" data-testid="prof-name">${opts}</select>
      </label>
      <button type="button" id="prof-load" data-testid="prof-load">Load</button>
      <button type="button" id="prof-validate" data-testid="prof-validate">Validate</button>
      <button type="button" id="prof-preview" data-testid="prof-preview">Diff preview</button>
      <button type="button" id="prof-save" data-testid="prof-save">Save</button>
    </div>
    <p class="meta">Secret env slots: ${secrets || "—"}</p>
    <textarea id="prof-fields" data-testid="prof-fields" rows="18" class="code">${esc(fieldsJson)}</textarea>
    <pre class="log" id="prof-msg" data-testid="prof-msg"></pre>
  `;
}

export function wireProfiles(): void {
  const msg = document.getElementById("prof-msg");
  const fieldsEl = document.getElementById("prof-fields") as HTMLTextAreaElement | null;
  const nameEl = document.getElementById("prof-name") as HTMLSelectElement | null;

  const parseFields = (): Record<string, unknown> => {
    if (!fieldsEl) return {};
    return JSON.parse(fieldsEl.value) as Record<string, unknown>;
  };

  document.getElementById("prof-load")?.addEventListener("click", () => {
    void (async () => {
      try {
        const name = nameEl?.value || "";
        const p = await getProfile(name);
        if (fieldsEl) fieldsEl.value = JSON.stringify(p.fields, null, 2);
        if (msg) msg.textContent = `loaded ${name}`;
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });

  document.getElementById("prof-validate")?.addEventListener("click", () => {
    void (async () => {
      try {
        const name = nameEl?.value || "";
        const result = await validateProfile(name, parseFields());
        if (msg) {
          msg.textContent = result.ok
            ? `OK\n${JSON.stringify(result.settings_summary, null, 2)}`
            : result.errors.join("\n");
        }
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });

  document.getElementById("prof-preview")?.addEventListener("click", () => {
    void (async () => {
      try {
        const name = nameEl?.value || "";
        const result = await saveProfile(name, parseFields(), false);
        if (msg) msg.textContent = result.diff || "(no diff)";
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });

  document.getElementById("prof-save")?.addEventListener("click", () => {
    void (async () => {
      try {
        const name = nameEl?.value || "";
        const result = await saveProfile(name, parseFields(), true);
        if (msg) {
          msg.textContent = result.saved
            ? `saved\n${result.diff}`
            : result.errors.join("\n");
        }
      } catch (err) {
        if (msg) msg.textContent = String(err);
      }
    })();
  });
}
