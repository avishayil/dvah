import { Page, expect } from "@playwright/test";

export const API = process.env.E2E_API_BASE ?? "http://localhost:8000";

/** Open a lab workspace and wait for its session to be created. */
export async function openLab(page: Page, id: string, mode: "learn" | "ctf" = "learn") {
  await page.goto(`/labs/${id}?mode=${mode}`);
  // The workspace stamps the session id on its root once created.
  await expect(page.locator("[data-session-id]")).toHaveAttribute(
    "data-session-id",
    /.+/,
    { timeout: 20_000 },
  );
}

export async function sessionId(page: Page): Promise<string> {
  const sid = await page.locator("[data-session-id]").getAttribute("data-session-id");
  if (!sid) throw new Error("no session id on the workspace root");
  return sid;
}

/**
 * Apply a fix by setting the Monaco model's value directly (fires the editor's onChange →
 * updates React state → the app persists it on the next run). Robust vs char-by-char typing.
 */
export async function applyFix(page: Page, fixPath: string, contents: string) {
  const base = fixPath.split("/").pop()!;
  // Ensure the editor + monaco global are ready and a model for this file exists.
  await page.waitForFunction(
    (b) => {
      const m = (window as unknown as { monaco?: any }).monaco;
      return !!m?.editor?.getModels?.().some((x: any) => x.uri.path.endsWith(b));
    },
    base,
    { timeout: 20_000 },
  );
  await page.evaluate(
    ({ b, code }) => {
      const monaco = (window as unknown as { monaco: any }).monaco;
      const model = monaco.editor.getModels().find((x: any) => x.uri.path.endsWith(b));
      model.setValue(code);
    },
    { b: base, code: contents },
  );
  // Let Monaco's change event → React onChange → setFiles commit before a run's saveAll
  // reads `files` (otherwise the run persists the stale vulnerable code).
  await page.waitForTimeout(500);
}

/** Click a run marker button and wait for the run to finish (buttons re-enable). */
export async function runMarker(page: Page, name: string) {
  // Unanchored: the "run all" button's accessible name is its aria-label
  // ("Run all four test markers"), so an anchored /^run all$/ wouldn't match it.
  await page.getByRole("button", { name: new RegExp(name, "i") }).first().click();
  // The result summary or test rows appear; the run-all button re-enables when done.
  await expect(page.getByRole("button", { name: /run all/i })).toBeEnabled({ timeout: 45_000 });
}

/** The data-state of each invariant chip on the board (scoped so Radix tab
 * triggers/content — which also carry data-state="active"/"inactive" — don't leak in). */
export async function boardStates(page: Page): Promise<string[]> {
  return page
    .locator('[data-tour="invariants"] [data-state]')
    .evaluateAll((els) => els.map((e) => e.getAttribute("data-state") ?? ""));
}
