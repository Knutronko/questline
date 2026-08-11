import {
  esc,
  ensureCsrf,
  getMeta,
  launchRun,
  launcherStatus,
  listDevices,
  listProfiles,
  listReporters,
  stopLaunch,
  type LauncherStatus,
} from "../api";

export async function renderLaunch(): Promise<string> {
  await ensureCsrf();
  const [meta, profiles, devices, reporters, status] = await Promise.all([
    getMeta(),
    listProfiles(),
    listDevices(),
    listReporters(),
    launcherStatus().catch(() => ({ launcher: { state: "idle" } as LauncherStatus })),
  ]);

  if (meta.read_only) {
    return `<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;
  }

  const profileOpts = (profiles.profiles || [])
    .map((p) => `<option value="${esc(p)}">${esc(p)}</option>`)
    .join("");
  const deviceOpts = [
    `<option value="">(profile default)</option>`,
    ...(devices.devices || []).map(
      (d) => `<option value="${esc(d.id)}">${esc(d.id)} · ${esc(d.platform)}</option>`,
    ),
  ].join("");
  const reporterChecks = (reporters.reporters || [])
    .map(
      (r) =>
        `<label class="check"><input type="checkbox" name="reporter" value="${esc(r)}"/> ${esc(r)}</label>`,
    )
    .join("");

  const st = status.launcher;
  return `
    <h1>Run launcher</h1>
    <p class="meta">Composes the same pytest / questline session flags as the CLI.
      Live events attach automatically via event forward → <a href="#/live">Live</a>.</p>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${profileOpts}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${deviceOpts}</select>
        </label>
        <label>markers <input id="launch-markers" placeholder="quest_demo" data-testid="launch-markers"/></label>
      </div>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/demo-tests"></textarea>
      </label>
      <div class="toolbar wrap">${reporterChecks || "<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start">Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop">Stop</button>
      </div>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${esc(JSON.stringify(st, null, 2))}</pre>
    ${devices.error ? `<p class="meta">devices: ${esc(devices.error)}</p>` : ""}
  `;
}

export function wireLaunch(): void {
  const statusEl = document.getElementById("launch-status");
  const refresh = async () => {
    try {
      const { launcher } = await launcherStatus();
      if (statusEl) statusEl.textContent = JSON.stringify(launcher, null, 2);
    } catch (err) {
      if (statusEl) statusEl.textContent = String(err);
    }
  };

  document.getElementById("launch-start")?.addEventListener("click", () => {
    void (async () => {
      const profile = (document.getElementById("launch-profile") as HTMLSelectElement).value;
      const device = (document.getElementById("launch-device") as HTMLSelectElement).value;
      const markers = (document.getElementById("launch-markers") as HTMLInputElement).value.trim();
      const rawTests = (document.getElementById("launch-tests") as HTMLTextAreaElement).value;
      const tests = rawTests
        .split(/\r?\n/)
        .map((s) => s.trim())
        .filter(Boolean);
      const reporters = Array.from(
        document.querySelectorAll<HTMLInputElement>('input[name="reporter"]:checked'),
      ).map((el) => el.value);
      const include = (document.getElementById("launch-quarantine") as HTMLInputElement)
        ?.checked;
      try {
        const { launcher } = await launchRun({
          profile,
          tests,
          markers: markers || undefined,
          device_serial: device || undefined,
          reporters: reporters.length ? reporters : undefined,
          include_quarantined: !!include,
        });
        if (statusEl) statusEl.textContent = JSON.stringify(launcher, null, 2);
        location.hash = "/live";
      } catch (err) {
        if (statusEl) statusEl.textContent = String(err);
      }
    })();
  });

  document.getElementById("launch-stop")?.addEventListener("click", () => {
    void (async () => {
      try {
        const { launcher } = await stopLaunch();
        if (statusEl) statusEl.textContent = JSON.stringify(launcher, null, 2);
      } catch (err) {
        if (statusEl) statusEl.textContent = String(err);
      }
    })();
  });

  void refresh();
  window.setInterval(() => {
    if (location.hash.replace(/^#\/?/, "").startsWith("launch")) void refresh();
  }, 2000);
}
