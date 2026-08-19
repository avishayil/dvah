import { test, expect } from "./support/setup";

test.beforeEach(({}, ti) => {
  test.skip(ti.project.name !== "chromium", "chromium only");
});

test("the full-screen guided demo plays and offers a jump into the lab", async ({ page }) => {
  await page.goto("/demo");

  // The full-screen player mounts on the first frame's full-frame beat.
  await expect(page.getByTestId("demo-player")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("demo-caption")).toBeVisible();
  await expect(page.getByTestId("demo-caption")).toContainText(/harness|exploit|runtime/i);
  // The pointer appears during the slide's click beat (after full → zoom), not at mount.
  await expect(page.getByTestId("demo-cursor")).toBeVisible({ timeout: 15_000 });

  // Pause autoplay, then step to the last frame.
  await page.getByRole("button", { name: /pause/i }).click();
  const next = page.getByRole("button", { name: /next step/i });
  for (let n = 0; n < 6; n++) {
    if (await next.isDisabled()) break;
    await next.click();
  }

  // The end frame offers a direct jump into the live lab.
  const open = page.getByTestId("open-dvah-001");
  await expect(open).toBeVisible();
  await expect(open).toHaveAttribute("href", /\/labs\/DVAH-001-plan-time-authorization/);
});
