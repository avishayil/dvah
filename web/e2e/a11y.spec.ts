import { test, expect } from "./support/setup";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

async function scan(page: import("@playwright/test").Page, exclude?: string) {
  let builder = new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]);
  if (exclude) builder = builder.exclude(exclude);
  const results = await builder.analyze();
  return results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
}

for (const path of ["/", "/labs", "/concepts", "/mutate"]) {
  test(`no serious a11y violations: ${path}`, async ({ page }) => {
    await page.goto(path);
    const serious = await scan(page);
    expect(serious.map((v) => v.id)).toEqual([]);
  });
}

test("no serious a11y violations: lab workspace", async ({ page }) => {
  await page.goto("/labs/DVAH-001-plan-time-authorization?mode=learn");
  await expect(page.locator("[data-session-id]")).toBeVisible();
  await page.keyboard.press("Escape"); // close the first-run tour overlay if present
  // Monaco injects its own complex ARIA (third-party widget); exclude it from the audit.
  const serious = await scan(page, ".monaco-editor");
  expect(
    serious.map((v) => v.id),
    JSON.stringify(serious.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }))),
  ).toEqual([]);
});
