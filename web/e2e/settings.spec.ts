import { test, expect } from "./support/setup";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

test("settings: generic Model & API section + key is masked, never leaked", async ({ page }) => {
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: /^settings$/i })).toBeVisible();
  // Generic Model & API section (not tutor-specific) + the single global run-mode control.
  await expect(page.getByRole("heading", { name: /model & api/i })).toBeVisible();
  await expect(page.getByRole("heading", { name: /^run mode$/i })).toBeVisible();
  await expect(page.getByRole("radio", { name: /deterministic/i })).toHaveAttribute("aria-checked", "true");

  // "Test connection" surfaces the disabled/unconfigured state as a structured message.
  await page.getByRole("button", { name: /test connection/i }).click();
  await expect(page.getByText(/✗|not enabled|not configured|no key/i).first()).toBeVisible();

  // Saving a key returns only a masked hint — the raw key never comes back.
  await page.getByLabel(/^provider$/i).selectOption("openai");
  await page.getByLabel(/api key/i).fill("sk-e2e-SECRET-XYZ");
  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().endsWith("/api/settings") && r.request().method() === "PUT",
    ),
    page.getByRole("button", { name: /^save settings$/i }).click(),
  ]);
  const body = await resp.text();
  expect(body).not.toContain("sk-e2e-SECRET-XYZ");
  expect(body).toContain("XYZ"); // masked hint keeps only the last few chars
});
