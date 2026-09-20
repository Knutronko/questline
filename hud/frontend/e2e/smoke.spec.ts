import { test, expect } from "@playwright/test";

test("HUD smoke: runs → test → steps", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByTestId("runs-table")).toBeVisible({ timeout: 15_000 });
  // Fixture AI calls + infra death-point live on run-a; the list is newest-first (run-b).
  const runA = page.locator('[data-testid="run-row"][data-run-id="run-a"]');
  await expect(runA).toBeVisible();
  await runA.locator("a").first().click();
  await expect(page.getByTestId("verdict-banner")).toBeVisible();
  await expect(page.getByTestId("ai-calls-table")).toBeVisible();
  await expect(page.getByTestId("ai-call-row").first()).toBeVisible();
  await expect(page.getByTestId("tests-table")).toBeVisible();
  await page.getByTestId("test-row").first().locator("a").click();
  await expect(page.getByTestId("test-title")).toBeVisible();
  await expect(page.getByTestId("step-timeline")).toBeVisible();
  await expect(page.getByTestId("step-row").first()).toBeVisible();
  await expect(page.getByTestId("death-point")).toBeVisible();
});

test("HUD control: launch mock → live → stop", async ({ page }) => {
  await page.goto("/#/launch");
  await expect(page.getByTestId("launch-form")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("launch-start").click();
  // Launcher navigates to live on success; status may briefly show running.
  await expect(page).toHaveURL(/#\/live/, { timeout: 10_000 });
  await page.goto("/#/launch");
  await expect(page.getByTestId("launch-status")).toBeVisible();
  await page.getByTestId("launch-stop").click();
  await expect(page.getByTestId("launch-status")).toContainText(/finished|stopping|idle|error|running/);
});

test("HUD perf: compare two fixture runs", async ({ page }) => {
  await page.goto("/#/perf");
  await expect(page.getByTestId("perf-series")).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("perf-load").click();
  await expect(page.getByTestId("perf-metric").first()).toBeVisible({ timeout: 10_000 });
  await page.getByTestId("perf-compare").click();
  await expect(page.getByTestId("perf-delta-table")).toBeVisible({ timeout: 10_000 });
});

test("HUD GameLens: snapshots → diff → gaps → ask agent", async ({ page }) => {
  await page.goto("/#/lens");
  await expect(page.getByTestId("lens-snapshots")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("lens-snap-row").first()).toBeVisible();
  await page.getByTestId("lens-open-diff").click();
  await expect(page.getByTestId("lens-diff-meta")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByTestId("lens-implications")).toBeVisible();
  await expect(page.getByTestId("lens-gaps")).toContainText("combat.damage");
  await expect(page.getByTestId("lens-gaps")).toContainText("snap-unset");
  await page.getByTestId("agent-run").click();
  await expect(page.getByTestId("agent-turn")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("agent-priorities")).toContainText("leak_count");
  await expect(page.getByTestId("agent-gaps")).toContainText("combat.damage");
});

test("HUD telemetry: lose is measured; snap-unset is a gap", async ({ page }) => {
  await page.goto("/#/lens/sessions");
  await expect(page.getByTestId("tel-sessions")).toBeVisible({ timeout: 15_000 });
  const unset = page.locator('[data-testid="tel-session-row"][data-session-id="sess-unset"]');
  await expect(unset).toBeVisible();
  await expect(unset).toContainText("lose");
  await expect(unset).toContainText("snap-unset");
  await unset.locator("a").click();
  await expect(page.getByTestId("tel-session-detail")).toBeVisible();
  await expect(page.getByTestId("tel-session-notes")).toContainText("measured play");
});
