/** Thin fetch wrapper for HUD REST. */

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

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${path}: ${text}`);
  }
  return (await res.json()) as T;
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
