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
