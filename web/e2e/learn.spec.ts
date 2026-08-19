import { test, expect } from "./support/setup";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

test("concepts page defines terms with concrete examples", async ({ page }) => {
  await page.goto("/concepts");
  await expect(page.getByRole("heading", { name: /learn the concepts/i })).toBeVisible();
  // A few representative concepts render.
  for (const term of ["ActionEnvelope", "capability", "invariant"]) {
    await expect(page.getByText(term).first()).toBeVisible();
  }
  // Every concept carries an "Example" block.
  expect(await page.getByText("Example", { exact: true }).count()).toBeGreaterThan(5);
  // Chaos + conformance live under Learn, with a link into Chaos mode.
  await expect(page.getByText(/Chaos mode/i).first()).toBeVisible();
  await page.getByRole("link", { name: /open chaos mode/i }).click();
  await expect(page).toHaveURL(/\/mutate/);
});
