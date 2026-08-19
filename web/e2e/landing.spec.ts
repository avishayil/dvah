import { test, expect } from "./support/setup";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

test("landing onboards a general engineer via the guided demo", async ({ page }) => {
  await page.goto("/");
  // Reassurance for non-security engineers.
  await expect(page.getByText(/no security background/i)).toBeVisible();
  // The loop is spelled out.
  for (const step of ["Exploit", "Trace", "Prove"]) {
    await expect(page.getByText(new RegExp(step, "i")).first()).toBeVisible();
  }

  // The primary CTA is a link into the full-screen guided demo of DVAH-001.
  const start = page.getByRole("link", { name: /start with dvah-001/i }).first();
  await expect(start).toBeVisible();
  await start.click();
  await expect(page).toHaveURL(/\/demo/);
  // The full-screen player shows the first frame + caption.
  await expect(page.getByTestId("demo-player")).toBeVisible();
  await expect(page.getByTestId("demo-caption")).toContainText(/harness/i);
});
