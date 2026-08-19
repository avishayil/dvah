import { test, expect } from "./support/setup";
import { LABS } from "./support/labs";
import { FIXES } from "./support/fixes";
import { openLab, applyFix, runMarker, boardStates, sessionId, API } from "./support/helpers";

// Labs run on desktop chromium (Monaco + full 3-col layout); responsive.spec covers mobile.
test.beforeEach(({}, testInfo) => { test.skip(testInfo.project.name !== "chromium", "labs run on chromium"); });

// Labs whose exploit is a run-through-a-plan (produce a trace). 009/012/013 prove via
// property/constructed-envelope tests, so they have no run-plan trace to assert.
const NO_TRACE = new Set([
  "DVAH-009-skill-upgrade",
  "DVAH-012-tool-rug-pull",
  "DVAH-013-race-to-the-bottom",
  // DVAH-014's exploit invokes the MCP tool provider directly (not via the broker),
  // so there is no run-plan trace to assert; the egress containment is proven by the test.
  "DVAH-014-mcp-egress",
]);

test.describe("exploit → trace → patch → prove", () => {
  for (const lab of LABS) {
    test(lab.id, async ({ page }) => {
      await openLab(page, lab.id);
      await expect(page.getByText(lab.title).first()).toBeVisible();
      await expect(page.getByText("What you're fixing")).toBeVisible();

      // 1) Exploit against the shipped vulnerable code → vulnerability reproduced.
      await runMarker(page, "exploit");
      await expect(page.getByText(/Vulnerability reproduced/i)).toBeVisible();
      expect(await boardStates(page)).toContain("broken");

      // 2) Trace shows why (for labs that run a plan).
      if (!NO_TRACE.has(lab.id)) {
        // Exercise the Trace tab in the UI (best-effort), then assert the trace itself via
        // the same API the tab calls — deterministic, and not subject to the headless
        // Radix tab-panel visibility quirk. Trace *rendering* is covered by the
        // trace-graph component test; trace *content* by backend summarize_trace tests.
        await page.getByRole("tab", { name: /^trace$/i }).click().catch(() => {});
        const sid = await sessionId(page);
        const taskId = await page.locator("select").first().inputValue();
        const res = await page.request.post(`${API}/api/sessions/${sid}/trace`, {
          data: { task_id: taskId },
        });
        const kinds = ((await res.json()).events ?? []).map((e: { kind: string }) => e.kind);
        expect(
          kinds.some((k: string) =>
            /executed|policy\.decision|denied|context\.compiled|provenance|delegate/.test(k),
          ),
        ).toBeTruthy();
        await page.getByRole("tab", { name: /^run$/i }).click().catch(() => {});
      }

      // 3) Apply the correct in-place fix, then prove it.
      await applyFix(page, lab.fixPath, FIXES[lab.id]);
      await runMarker(page, "run all");

      await expect(page.getByText(/Fixed — the invariant holds/i)).toBeVisible();
      const states = await boardStates(page);
      expect(states.length).toBeGreaterThan(0);
      expect(states.every((s) => s === "hold")).toBeTruthy();
    });
  }
});
