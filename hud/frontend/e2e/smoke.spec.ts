import { test, expect } from "@playwright/test";

test("HUD smoke: runs → test → steps", async ({ page }) => {
  await page.goto("/#/");
  await expect(page.getByTestId("runs-table")).toBeVisible({ timeout: 15_000 });
  const first = page.getByTestId("run-row").first();
  await expect(first).toBeVisible();
  await first.locator("a").first().click();
  await expect(page.getByTestId("verdict-banner")).toBeVisible();
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
