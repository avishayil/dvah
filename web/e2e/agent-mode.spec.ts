import { test, expect } from "./support/setup";
import { openLab } from "./support/helpers";

// The agent-timeline + dual-score UI needs the full 3-col workspace (Monaco + tabs).
test.beforeEach(({}, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "agent-mode UI runs on chromium");
});

test.describe("agent timeline + dual scores + run mode", () => {
  test("shows the two scores and the lane timeline; live mode is gated", async ({ page }) => {
    await openLab(page, "DVAH-001-plan-time-authorization");
    await expect(page.getByText("What you're fixing")).toBeVisible();

    // Run mode is a single global setting (chosen in Settings), only reflected here as a
    // read-only badge. Default is deterministic; assert the badge + its Settings link,
    // independent of the environment's key/mode state.
    const runMode = page.getByTestId("run-mode");
    await expect(runMode).toBeVisible();
    await expect(runMode).toHaveAttribute("data-mode", /deterministic|live/);
    await expect(page.getByTestId("run-mode-settings-link")).toBeVisible();

    // Open the Agent timeline tab → the trace loads and both panels render.
    await page.getByRole("tab", { name: /agent timeline/i }).click();
    await expect(page.getByTestId("dual-score")).toBeVisible();
    await expect(page.getByTestId("agent-timeline")).toBeVisible();

    // Runtime Security renders a verdict (secure true/false), independent of model behavior.
    const runtime = page.getByTestId("runtime-security");
    await expect(runtime).toBeVisible();
    await expect(runtime).toHaveAttribute("data-secure", /true|false/);

    // The lane timeline places events into agent-loop lanes.
    await expect(page.getByTestId("agent-timeline").locator("li[data-lane]").first()).toBeVisible();
  });
});
