import {
  esc,
  ensureCsrf,
  getMeta,
  launchRun,
  launcherStatus,
  listConfigs,
  listDevices,
  listProfiles,
  listReporters,
  stopLaunch,
  type LauncherStatus,
} from "../api";

type SuitePreset = {
  id: string;
  label: string;
  config: string;
  profile: string;
  tests: string;
  live_target: boolean;
  note: string;
};

const PRESETS: SuitePreset[] = [
  {
    id: "mock",
    label: "Mock demo",
    config: "questline.toml",
    profile: "mock",
    tests: "examples/demo-tests",
    live_target: false,
    note: "No Unity. CI-style mock driver.",
  },
  {
    id: "wire-editor",
    label: "Wire Editor",
    config: "examples/wire-smoke/questline.toml",
    profile: "editor",
    tests: "examples/wire-smoke",
    live_target: true,
    note: "Unity Play + Wire on :13000. Device picker stays empty (OK).",
  },
  {
    id: "wire-android",
    label: "Wire Android",
    config: "examples/wire-smoke/questline.toml",
    profile: "android_local",
    tests: "examples/wire-smoke",
    live_target: true,
    note: "Dev APK + adb. Pick a serial if more than one device.",
  },
];

export async function renderLaunch(): Promise<string> {
  await ensureCsrf();
  let meta;
  let configs: {
    project_root: string;
    active: string;
    configs: Array<{ path: string; absolute: string }>;
  };
  let reporters: { reporters: string[] };
  let status: { launcher: LauncherStatus };

  try {
    [meta, configs, reporters, status] = await Promise.all([
      getMeta(),
      listConfigs().catch(() => ({
        project_root: "",
        active: "",
        configs: [{ path: "questline.toml", absolute: "questline.toml" }],
      })),
      listReporters().catch(() => ({ reporters: ["console"] })),
      launcherStatus().catch(() => ({
        launcher: { state: "idle" } as LauncherStatus,
      })),
    ]);
  } catch (err) {
    return `<h1>Launch</h1>
      <div class="empty" data-testid="launch-error">
        Failed to load launcher APIs: ${esc(String(err))}<br/>
        Stop the old <code>questline hud</code> process and start it again from
        <code>D:\\dev\\questline</code>.
      </div>`;
  }

  if (meta.read_only) {
    return `<h1>Launch</h1>
      <div class="empty" data-testid="launch-readonly">
        HUD is in <code>--read-only</code> mode. Mutating APIs are disabled.
      </div>`;
  }

  const defaultConfig =
    configs.configs.find((c) => c.path.replace(/\\/g, "/") === "questline.toml")?.path ||
    configs.configs[0]?.path ||
    "questline.toml";

  const profiles = await listProfiles(defaultConfig);
  const devices = await listDevices();

  const configOpts = (configs.configs || [])
    .map((c) => {
      const selected = c.path === defaultConfig ? "selected" : "";
      return `<option value="${esc(c.path)}" ${selected}>${esc(c.path)}</option>`;
    })
    .join("");

  const profileOptsPreferred = (profiles.profiles || [])
    .map((p) => {
      const preferred = profiles.profiles.includes("editor")
        ? "editor"
        : profiles.profiles.includes("mock")
          ? "mock"
          : profiles.profiles[0] || "";
      return `<option value="${esc(p)}" ${p === preferred ? "selected" : ""}>${esc(p)}</option>`;
    })
    .join("");

  const deviceOpts = [
    `<option value="">(no adb pin — OK for Editor)</option>`,
    ...(devices.devices || []).map(
      (d) => `<option value="${esc(d.id)}">${esc(d.id)} · ${esc(d.platform)}</option>`,
    ),
  ].join("");

  const reporterChecks = (reporters.reporters || [])
    .map(
      (r) =>
        `<label class="check"><input type="checkbox" name="reporter" value="${esc(r)}" ${r === "console" ? "checked" : ""}/> ${esc(r)}</label>`,
    )
    .join("");

  const presets = PRESETS.map(
    (p) =>
      `<button type="button" class="preset" data-preset="${esc(p.id)}" title="${esc(p.note)}">${esc(p.label)}</button>`,
  ).join("");

  const st = status.launcher;
  const busy = ["starting", "running", "stopping"].includes(st.state || "");
  const deviceHint =
    devices.hint ||
    (devices.devices?.length
      ? `${devices.devices.length} adb device(s)`
      : "No adb devices — normal for Unity Editor Wire.");

  const busyBanner = busy
    ? `<div class="empty" data-testid="launch-busy">
        A managed run is <strong>${esc(st.state || "")}</strong>
        (job <code>${esc(st.job_id || "")}</code>, profile
        <code>${esc(st.profile || "")}</code>).
        <a href="#/live">Open Live</a> to watch it, or <strong>Stop</strong> below
        before launching another.
      </div>`
    : "";

  return `
    <h1>Run launcher</h1>
    ${busyBanner}
    <p class="meta">Profiles come from <code>questline.toml</code> (not from Unity being open).
      Unity Play + Wire = use preset <strong>Wire Editor</strong> or profile <code>editor</code>.
      Device list is <em>adb only</em> — Editor does not appear there.</p>
    <div class="toolbar" data-testid="launch-presets">
      <span class="meta">Presets:</span> ${presets}
    </div>
    <div class="panel" data-testid="launch-form">
      <div class="toolbar">
        <label>config
          <select id="launch-config" data-testid="launch-config">${configOpts}</select>
        </label>
        <label>profile
          <select id="launch-profile" data-testid="launch-profile">${profileOptsPreferred}</select>
        </label>
        <label>device
          <select id="launch-device" data-testid="launch-device">${deviceOpts}</select>
        </label>
        <button type="button" id="launch-refresh-devices" data-testid="launch-refresh-devices">Refresh devices</button>
      </div>
      <p class="meta" id="launch-device-hint" data-testid="launch-device-hint">${esc(deviceHint)}</p>
      ${devices.error ? `<p class="meta">adb error: ${esc(devices.error)}</p>` : ""}
      <label class="block">markers <input id="launch-markers" placeholder="optional -m expression" data-testid="launch-markers"/></label>
      <label class="block">tests (one path/nodeid per line)
        <textarea id="launch-tests" rows="4" data-testid="launch-tests" placeholder="examples/wire-smoke">examples/demo-tests</textarea>
      </label>
      <div class="toolbar wrap">${reporterChecks || "<span class='meta'>no reporters</span>"}</div>
      <label class="check"><input type="checkbox" id="launch-quarantine"/> include quarantined</label>
      <label class="check"><input type="checkbox" id="launch-live" data-testid="launch-live"/> QUESTLINE_LIVE_TARGET=1 (required for wire-smoke)</label>
      <div class="toolbar">
        <button type="button" id="launch-start" data-testid="launch-start" ${busy ? "disabled" : ""}>Launch</button>
        <button type="button" id="launch-stop" data-testid="launch-stop" ${busy ? "" : "disabled"}>Stop</button>
        ${busy ? `<a class="button" href="#/live" data-testid="launch-open-live">Open Live</a>` : ""}
      </div>
      <p class="meta">Active project: <code>${esc(configs.project_root)}</code></p>
    </div>
    <h2>Status</h2>
    <pre class="log" id="launch-status" data-testid="launch-status">${esc(JSON.stringify(st, null, 2))}</pre>
  `;
}

export function wireLaunch(): void {
  const statusEl = document.getElementById("launch-status");
  const configEl = document.getElementById("launch-config") as HTMLSelectElement | null;
  const profileEl = document.getElementById("launch-profile") as HTMLSelectElement | null;
  const deviceEl = document.getElementById("launch-device") as HTMLSelectElement | null;
  const testsEl = document.getElementById("launch-tests") as HTMLTextAreaElement | null;
  const liveEl = document.getElementById("launch-live") as HTMLInputElement | null;
  const hintEl = document.getElementById("launch-device-hint");

  const reloadProfiles = async () => {
    if (!configEl || !profileEl) return;
    try {
      const data = await listProfiles(configEl.value);
      const preferred = data.profiles.includes("editor")
        ? "editor"
        : data.profiles[0] || "";
      profileEl.innerHTML = data.profiles
        .map(
          (p) =>
            `<option value="${esc(p)}" ${p === preferred ? "selected" : ""}>${esc(p)}</option>`,
        )
        .join("");
    } catch (err) {
      if (statusEl) statusEl.textContent = String(err);
    }
  };

  const reloadDevices = async () => {
    if (!deviceEl) return;
    try {
      const devices = await listDevices();
      deviceEl.innerHTML = [
        `<option value="">(no adb pin — OK for Editor)</option>`,
        ...(devices.devices || []).map(
          (d) =>
            `<option value="${esc(d.id)}">${esc(d.id)} · ${esc(d.platform)}</option>`,
        ),
      ].join("");
      if (hintEl) {
        hintEl.textContent =
          devices.hint ||
          (devices.devices?.length
            ? `${devices.devices.length} adb device(s)`
            : "No adb devices — normal for Unity Editor Wire.");
      }
    } catch (err) {
      if (hintEl) hintEl.textContent = String(err);
    }
  };

  configEl?.addEventListener("change", () => {
    void reloadProfiles();
  });

  document.getElementById("launch-refresh-devices")?.addEventListener("click", () => {
    void reloadDevices();
  });

  document.querySelectorAll<HTMLButtonElement>(".preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.preset || "";
      const preset = PRESETS.find((p) => p.id === id);
      if (!preset) return;
      if (configEl) {
        // Ensure option exists
        const has = Array.from(configEl.options).some((o) => o.value === preset.config);
        if (!has) {
          const opt = document.createElement("option");
          opt.value = preset.config;
          opt.textContent = preset.config;
          configEl.appendChild(opt);
        }
        configEl.value = preset.config;
      }
      if (testsEl) testsEl.value = preset.tests;
      if (liveEl) liveEl.checked = preset.live_target;
      void (async () => {
        await reloadProfiles();
        if (profileEl) profileEl.value = preset.profile;
      })();
    });
  });

  const refresh = async () => {
    try {
      const { launcher } = await launcherStatus();
      if (statusEl) statusEl.textContent = JSON.stringify(launcher, null, 2);
      const busy = ["starting", "running", "stopping"].includes(launcher.state || "");
      const startBtn = document.getElementById("launch-start") as HTMLButtonElement | null;
      const stopBtn = document.getElementById("launch-stop") as HTMLButtonElement | null;
      if (startBtn) startBtn.disabled = busy;
      if (stopBtn) stopBtn.disabled = !busy;
    } catch (err) {
      if (statusEl) statusEl.textContent = String(err);
    }
  };

  document.getElementById("launch-start")?.addEventListener("click", () => {
    void (async () => {
      const profile = profileEl?.value || "";
      const device = deviceEl?.value || "";
      const markers = (document.getElementById("launch-markers") as HTMLInputElement).value.trim();
      const rawTests = testsEl?.value || "";
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
          config: configEl?.value || undefined,
          live_target: !!liveEl?.checked,
        });
        if (statusEl) statusEl.textContent = JSON.stringify(launcher, null, 2);
        location.hash = "/live";
      } catch (err) {
        const msg = String(err);
        if (statusEl) statusEl.textContent = msg;
        // Already running → open Live instead of leaving the operator stuck.
        if (/\b409\b/.test(msg) && /already/i.test(msg)) {
          location.hash = "/live";
        }
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
