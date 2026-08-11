/** Thin fetch wrapper for HUD REST (reads + CSRF mutators). */

export type RunSummary = {
  id: string;
  profile: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_s?: number | null;
  driver?: string | null;
  device?: string | null;
  passed: number;
  failed: number;
  skipped: number;
  error: number;
  total: number;
  infra_failures: number;
  test_failures: number;
  authoring_failures: number;
  unknown_failures: number;
};

export type TestSummary = {
  id: string;
  run_id: string;
  nodeid: string;
  status: string;
  verdict?: string | null;
  error_type?: string | null;
  error_message?: string | null;
  feature_id?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_s?: number | null;
  death_step_name?: string | null;
};

export type Meta = {
  read_only: boolean;
  control_center: boolean;
  smoke?: boolean;
  config_path: string | null;
  project_root: string;
  quarantine_path: string;
  reporters: string[];
};

export type LauncherStatus = {
  job_id: string | null;
  state: string;
  profile: string | null;
  pid: number | null;
  argv: string[];
  started_at: number | null;
  finished_at: number | null;
  returncode: number | null;
  error: string | null;
  device_serial: string | null;
};

let csrfToken: string | null = null;

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  const text = await res.text();
  const looksHtml =
    /^\s*</.test(text) ||
    (res.headers.get("content-type") || "").includes("text/html");
  if (looksHtml) {
    throw new Error(
      `${res.status} ${path}: got HTML instead of JSON. ` +
        `Restart questline hud (old process missing new /api routes).`,
    );
  }
  if (!res.ok) {
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  try {
    return JSON.parse(text) as T;
  } catch (err) {
    throw new Error(`${path}: invalid JSON (${String(err)})`);
  }
}

export async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  const data = await getJson<{ csrf_token: string }>("/api/csrf");
  csrfToken = data.csrf_token;
  return csrfToken;
}

async function mutateJson<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const token = await ensureCsrf();
  const res = await fetch(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": token,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function getMeta(): Promise<Meta> {
  return getJson("/api/meta");
}

export function listRuns(params: {
  profile?: string;
  status?: string;
}): Promise<{ runs: RunSummary[]; empty: boolean }> {
  const q = new URLSearchParams();
  if (params.profile) q.set("profile", params.profile);
  if (params.status) q.set("status", params.status);
  const qs = q.toString();
  return getJson(`/api/runs${qs ? `?${qs}` : ""}`);
}

export function getRun(runId: string): Promise<{
  run: RunSummary;
  tests: TestSummary[];
  banner: {
    infra_failures: number;
    test_failures: number;
    authoring_failures: number;
    unknown_failures: number;
  };
}> {
  return getJson(`/api/runs/${encodeURIComponent(runId)}`);
}

export function getTest(
  runId: string,
  testId: string,
): Promise<{
  test: TestSummary;
  steps: Array<Record<string, unknown>>;
  death_point: Record<string, unknown>;
  artifacts: Array<Record<string, unknown>>;
  history: Array<Record<string, unknown>>;
}> {
  return getJson(
    `/api/runs/${encodeURIComponent(runId)}/tests/${encodeURIComponent(testId)}`,
  );
}

export function getTrends(limit = 50): Promise<{
  series: Array<Record<string, unknown>>;
  flaky_tests: Array<Record<string, unknown>>;
}> {
  return getJson(`/api/trends?limit=${limit}`);
}

export function listProfiles(config?: string): Promise<{ profiles: string[]; path: string }> {
  const q = config ? `?config=${encodeURIComponent(config)}` : "";
  return getJson(`/api/profiles${q}`);
}

export function listConfigs(): Promise<{
  project_root: string;
  active: string;
  configs: Array<{ path: string; absolute: string }>;
}> {
  return getJson("/api/configs");
}

export function listDevices(): Promise<{
  devices: Array<{
    id: string;
    platform: string;
    api_level: number | null;
    caps: Record<string, string>;
  }>;
  error?: string;
  hint?: string | null;
}> {
  return getJson("/api/devices");
}

export function getProfile(name: string): Promise<{
  name: string;
  path: string;
  fields: Record<string, unknown>;
  secret_env_names: string[];
}> {
  return getJson(`/api/profiles/${encodeURIComponent(name)}`);
}

export function validateProfile(
  name: string,
  fields: Record<string, unknown>,
): Promise<{ ok: boolean; errors: string[]; settings_summary: unknown }> {
  return mutateJson("POST", `/api/profiles/${encodeURIComponent(name)}/validate`, {
    fields,
    apply: false,
  });
}

export function saveProfile(
  name: string,
  fields: Record<string, unknown>,
  apply: boolean,
): Promise<{
  ok: boolean;
  errors: string[];
  diff: string;
  saved: boolean;
}> {
  return mutateJson("POST", `/api/profiles/${encodeURIComponent(name)}`, {
    fields,
    apply,
  });
}

export function listReporters(): Promise<{ reporters: string[] }> {
  return getJson("/api/reporters");
}

export function launcherStatus(): Promise<{ launcher: LauncherStatus }> {
  return getJson("/api/launcher");
}

export function launchRun(body: {
  profile: string;
  tests?: string[];
  markers?: string;
  device_serial?: string;
  reporters?: string[];
  include_quarantined?: boolean;
  config?: string;
  live_target?: boolean;
}): Promise<{ launcher: LauncherStatus }> {
  return mutateJson("POST", "/api/launcher/start", body);
}

export function stopLaunch(): Promise<{ launcher: LauncherStatus }> {
  return mutateJson("POST", "/api/launcher/stop");
}

export function listQuarantine(): Promise<{
  path: string;
  entries: Array<Record<string, unknown>>;
}> {
  return getJson("/api/quarantine");
}

export function addQuarantine(body: {
  test_id: string;
  reason: string;
  owner: string;
  exit_criteria: string;
  issue?: string;
  feature?: string;
}): Promise<{ entry: Record<string, unknown> }> {
  return mutateJson("POST", "/api/quarantine", body);
}

export function removeQuarantine(testId: string): Promise<{ removed: string }> {
  return mutateJson(
    "DELETE",
    `/api/quarantine?test_id=${encodeURIComponent(testId)}`,
  );
}

export function auditQuarantine(body?: {
  tests?: string[];
  rootdir?: string;
}): Promise<{
  ok: boolean;
  ledger_only: string[];
  marker_only: string[];
  summary: string;
}> {
  return mutateJson("POST", "/api/quarantine/audit", body || {});
}

export function getPerf(runId: string): Promise<{
  run_id: string;
  found: boolean;
  summary: Record<string, Record<string, number>>;
  series: Record<string, Array<{ t?: string; v?: number; test_id?: string }>>;
}> {
  return getJson(`/api/perf/${encodeURIComponent(runId)}`);
}

export function comparePerf(
  a: string,
  b: string,
): Promise<{
  run_a: string;
  run_b: string;
  deltas: Array<{
    metric: string;
    a: Record<string, number>;
    b: Record<string, number>;
    delta_avg: number | null;
  }>;
  series_a: Record<string, Array<{ t?: string; v?: number }>>;
  series_b: Record<string, Array<{ t?: string; v?: number }>>;
}> {
  return getJson(
    `/api/perf/compare?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`,
  );
}

export function getPerfCorrelation(limit = 50): Promise<{
  tests: Array<{
    nodeid: string;
    points: Array<{ run_id: string; duration_s: number | null; passed: boolean }>;
    runs: number;
    passed: number;
    failed: number;
  }>;
}> {
  return getJson(`/api/perf/correlation?limit=${limit}`);
}

export function artifactUrl(path: string): string {
  return `/api/artifacts/file?path=${encodeURIComponent(path)}`;
}

export function fmtDur(s: number | null | undefined): string {
  if (s == null || Number.isNaN(s)) return "—";
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const r = s - m * 60;
  return `${m}m ${r.toFixed(0)}s`;
}

export function esc(s: unknown): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
