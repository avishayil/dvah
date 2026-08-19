import { test, expect } from "./support/setup";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "mobile", "mobile viewport only"); });

test("catalog + workspace are usable on a phone", async ({ page }) => {
  await page.goto("/labs");
  await expect(page.locator('[data-tour="lab-table"]')).toBeVisible();

  await page.goto("/labs/DVAH-001-plan-time-authorization?mode=learn");
  await expect(page.locator("[data-session-id]")).toBeVisible({ timeout: 20_000 });

  // The 3-col workspace stacks below lg — no horizontal overflow on a phone.
  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 2,
  );
  expect(overflows).toBeFalsy();
});
