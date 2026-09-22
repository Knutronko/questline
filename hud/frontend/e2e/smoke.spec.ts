import { test, expect } from "@playwright/test";

test("HUD unity chip: Ensure Editor stays allow-listed", async ({ page }) => {
  await page.goto("/#/launch");
  await expect(page.getByTestId("unity-chip")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("unity-cli")).not.toHaveText("CLI …", { timeout: 40_000 });
  await page.getByTestId("unity-ensure").click();
  await expect(page.getByTestId("unity-ensure")).toBeEnabled({ timeout: 40_000 });
  const chip = await page.getByTestId("unity-chip").innerText();
  expect(chip).not.toMatch(/evalToken/i);
  expect(chip).not.toMatch(/\\Users\\/);
  expect(chip).not.toMatch(/\/Users\//);
  await expect(page.getByTestId("unity-detail")).not.toHaveText("");
});

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

test("HUD agents: triage run + diagnose test", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByTestId("runs-table")).toBeVisible({ timeout: 15_000 });
  const runA = page.locator('[data-testid="run-row"][data-run-id="run-a"]');
  await runA.locator("a").first().click();
  await expect(page.getByTestId("triage-run")).toBeVisible();
  await page.getByTestId("triage-run").click();
  await expect(page.getByTestId("agent-task").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("triage-clusters")).toBeVisible();
  await page.locator('[data-testid="test-row"][data-test-id="t-infra"] a').click();
  await expect(page.getByTestId("diagnose-test")).toBeVisible();
  await page.getByTestId("diagnose-test").click();
  await expect(page.getByTestId("agent-task").first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("diagnose-msg")).toContainText("diagnosed");
});

test("HUD eval: history + compare two fixture runs", async ({ page }) => {
  await page.goto("/#/eval");
  await expect(page.getByTestId("eval-table")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("eval-row").first()).toBeVisible();
  await page.getByTestId("eval-compare").click();
  await expect(page.getByTestId("eval-delta-table")).toBeVisible({ timeout: 10_000 });
});

test("HUD generate: spec writes pytest and gate runs it", async ({ page }) => {
  await page.goto("/#/generate");
  await expect(page.getByTestId("gen-form")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("gen-tpl-ping")).toBeVisible();
  await page.getByTestId("gen-tpl-blank").click();
  await expect(page.getByTestId("gen-spec")).toHaveValue(/^\s*1\.\s*\n\s*do:/);
  await page.getByTestId("gen-tpl-combat").click();
  await expect(page.getByTestId("gen-spec")).toHaveValue(/amber is 50/);
  await page.getByTestId("gen-tpl-ping").click();
  await expect(page.getByTestId("gen-spec")).toHaveValue(/Ping hook returns pong/);
  await page.getByTestId("gen-run").click();
  await expect(page.getByTestId("gen-gate")).toContainText("executed=true", {
    timeout: 45_000,
  });
  await expect(page.getByTestId("gen-gate")).toContainText("accepted=true");
  await expect(page.getByTestId("gen-launch")).toHaveCount(0);
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
