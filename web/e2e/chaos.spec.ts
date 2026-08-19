import { test, expect } from "./support/setup";
import { API } from "./support/helpers";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

test("chaos mode runs and reveal matches the API", async ({ page, request }) => {
  await page.goto("/mutate");
  await expect(page.getByRole("heading", { name: /chaos mode/i })).toBeVisible();

  // Deterministic seed; reveal on so we can compare to the API.
  await page.getByLabel(/seed/i).fill("1");
  await page.getByLabel(/count/i).fill("2");
  await page.getByLabel(/reveal/i).check();
  await page.getByRole("button", { name: /^mutate$/i }).click();

  // The board renders and reveals the toggled defeats.
  await expect(page.locator("[data-state]").first()).toBeVisible();
  await expect(page.getByText(/revealed defeats:/i)).toBeVisible();

  // Parity: the same seed/count via the API reveals the same defeat set.
  const res = await request.post(`${API}/api/mutate`, {
    data: { seed: 1, count: 2, reveal: true },
  });
  const body = await res.json();
  for (const flag of body.revealed as string[]) {
    await expect(page.getByText(new RegExp(flag))).toBeVisible();
  }
});
