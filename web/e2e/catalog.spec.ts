import { test, expect } from "./support/setup";
import { LABS } from "./support/labs";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

test("catalog lists all labs, ordered, with difficulty + what-you'll-learn", async ({ page }) => {
  await page.goto("/labs");
  const table = page.locator('[data-tour="lab-table"]');
  await expect(table).toBeVisible();
  // All 13 lab ids present, DVAH-001 first (beginner→advanced order).
  for (const lab of LABS) {
    await expect(table.getByText(lab.title).first()).toBeVisible();
  }
  // The catalog shows short ids (routes resolve by prefix); DVAH-001 is first.
  await expect(table.getByText("DVAH-001", { exact: true }).first()).toBeVisible();
  // Difficulty + estimated time surfaced.
  await expect(table.getByText(/easy|medium|hard/i).first()).toBeVisible();
  await expect(table.getByText(/~\d+ min/).first()).toBeVisible();
});

test("learn/ctf toggle flips the lab links", async ({ page }) => {
  await page.goto("/labs");
  const firstRow = page.locator('[data-tour="lab-table"] tbody tr').first();
  await expect(firstRow.getByRole("link").first()).toHaveAttribute("href", /mode=learn/);
  await page.getByRole("button", { name: /^ctf$/i }).click();
  await expect(firstRow.getByRole("link").first()).toHaveAttribute("href", /mode=ctf/);
});
