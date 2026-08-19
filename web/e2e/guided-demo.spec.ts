import { test, expect } from "./support/setup";
import { boardStates } from "./support/helpers";

// The guided auto-solve demo runs the full DVAH-001 loop hands-off: exploit (red) →
// apply the reference fix → re-run to green. Chromium only (Monaco + 3-col workspace).
test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "guided demo runs on chromium");
});

test("guided DVAH-001 demo auto-solves to a green board", async ({ page }) => {
  // Two grader runs (exploit + prove) plus narrated dwell — allow generous headroom.
  test.setTimeout(150_000);
  await page.goto("/labs/DVAH-001-plan-time-authorization?mode=learn&demo=1");

  // The narrated overlay appears with its first caption.
  const demo = page.getByTestId("guided-demo");
  await expect(demo).toBeVisible();
  await expect(page.getByTestId("guided-demo-caption")).toContainText(/harness/i);

  // It auto-advances: run exploit → apply fix → prove. Wait for the board to hold.
  await expect
    .poll(async () => {
      const s = await boardStates(page);
      return s.length > 0 && s.every((x) => x === "hold");
    }, { timeout: 120_000, message: "invariant board should turn green (all hold)" })
    .toBe(true);

  // Having reached green, the narrated demo advances to its final step.
  await expect(page.getByRole("button", { name: /finish the demo/i })).toBeVisible({
    timeout: 30_000,
  });
});
