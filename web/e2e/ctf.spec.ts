import { test, expect } from "./support/setup";
import { openLab, sessionId, API } from "./support/helpers";

test.beforeEach(({}, ti) => { test.skip(ti.project.name !== "chromium", "chromium only"); });

const LAB = "DVAH-001-plan-time-authorization";

test("ctf mode locks hints + solution", async ({ page, request }) => {
  await openLab(page, LAB, "ctf");
  const sid = await sessionId(page);

  // Server-enforced: the solution endpoint is 403 for a ctf session.
  const res = await request.get(`${API}/api/challenges/${LAB}/solution?session_id=${sid}`);
  expect(res.status()).toBe(403);

  // The Walkthrough drawer shows a locked state instead of the reveal buttons.
  await page.getByRole("button", { name: /walkthrough/i }).click();
  await expect(page.getByText(/lock/i).first()).toBeVisible();
});
