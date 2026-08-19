import { test, expect } from "@playwright/test";
import { openLab } from "./support/helpers";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

// Each test gets a fresh context (empty localStorage), so the first-run tour auto-starts.
test("workspace tour auto-starts on first visit and can be replayed", async ({ page }) => {
  await openLab(page, "DVAH-001-plan-time-authorization");

  const popover = page.locator(".driver-popover");
  await expect(popover).toBeVisible({ timeout: 15_000 });

  // Dismiss it, then replay via the "Tour" trigger (aria-label "Take the guided tour").
  await page.keyboard.press("Escape");
  await expect(popover).toBeHidden();
  await page.getByRole("button", { name: /take the guided tour/i }).click();
  await expect(popover).toBeVisible();
});
