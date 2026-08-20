import fs from "node:fs";
import path from "node:path";
import type { Locator, Page } from "@playwright/test";
import { test, expect } from "./support/setup";
import { openLab, applyFix, runMarker, boardStates } from "./support/helpers";
import { FIXES } from "./support/fixes";

// Capture the REAL DVAH-001 states for the full-screen cursor-driven guided demo. Guarded:
// only runs when CAPTURE_DEMO=1 (via `npm run capture:demo`) so the normal e2e suite never
// depends on it. Deterministic (no live model).
//
// Every shot is an ELEMENT screenshot of the whole workspace container ([data-session-id]) —
// so it captures the full 3-column layout regardless of any horizontal overflow, is never a
// cropped viewport, and excludes the global nav chrome. Each shot is gated on a content
// assertion (no loading frames). Per frame we record, RELATIVE TO THE CAPTURED ELEMENT (as
// %): the cursor target the pointer moves to + clicks next, and a `focus` rect = the region
// the player zooms into. Written to manifest.json, which drives both /demo and site/demo.html.
const LAB = "DVAH-001-plan-time-authorization";
const PUBLIC_DIR = path.resolve(__dirname, "..", "public", "demo");
const SITE_DIR = path.resolve(__dirname, "..", "..", "site", "demo");
// After the run-panel overflow fix the 3 columns (320 + 1fr + 420) fit at this width.
const VW = 1680;
const VH = 1050;

type Rect = { xPct: number; yPct: number; wPct: number; hPct: number };
type Frame = {
  image: string;
  caption: string;
  cursor: { xPct: number; yPct: number } | null;
  focus: Rect | null;
  click: boolean;
  dwellMs: number;
};

// Capture at 2× device scale so the frames stay crisp when the /demo player magnifies them.
test.use({ viewport: { width: 1680, height: 1050 }, deviceScaleFactor: 2 });

test.beforeEach(({}, ti) => {
  test.skip(!process.env.CAPTURE_DEMO, "capture-only (set CAPTURE_DEMO=1)");
  test.skip(ti.project.name !== "chromium", "chromium only");
});

test("capture DVAH-001 guided-demo frames + manifest", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: VW, height: VH });

  fs.mkdirSync(PUBLIC_DIR, { recursive: true });
  fs.mkdirSync(SITE_DIR, { recursive: true });

  const frames: Frame[] = [];

  // The workspace container we screenshot; all coords below are % of ITS box.
  const stage = () => page.locator("[data-session-id]");
  async function stageBox() {
    const b = await stage().boundingBox();
    if (!b) throw new Error("workspace container [data-session-id] not found");
    return b;
  }

  // Center of `target` as a % of the captured element box.
  async function pct(target: Locator, box: { x: number; y: number; width: number; height: number }) {
    const t = await target.first().boundingBox();
    if (!t) return null;
    return {
      xPct: +(((t.x + t.width / 2 - box.x) / box.width) * 100).toFixed(2),
      yPct: +(((t.y + t.height / 2 - box.y) / box.height) * 100).toFixed(2),
    };
  }

  // Bounding rect of `target` as a % of the captured element box (the zoom-to region).
  async function rect(target: Locator, box: { x: number; y: number; width: number; height: number }): Promise<Rect | null> {
    const t = await target.first().boundingBox();
    if (!t) return null;
    const clamp = (v: number) => Math.max(0, Math.min(100, v));
    const xPct = clamp(((t.x - box.x) / box.width) * 100);
    const yPct = clamp(((t.y - box.y) / box.height) * 100);
    return {
      xPct: +xPct.toFixed(2),
      yPct: +yPct.toFixed(2),
      wPct: +Math.min(100 - xPct, (t.width / box.width) * 100).toFixed(2),
      hPct: +Math.min(100 - yPct, (t.height / box.height) * 100).toFixed(2),
    };
  }

  async function shoot(
    name: string,
    caption: string,
    cursorTo: Locator | null,
    focusEl: Locator | null,
    dwellMs: number,
  ) {
    const box = await stageBox();
    const cursor = cursorTo ? await pct(cursorTo, box) : null;
    const focus = focusEl ? await rect(focusEl, box) : null;
    const file = path.join(PUBLIC_DIR, name);
    await stage().screenshot({ path: file }); // element screenshot — full workspace, uncut.
    fs.copyFileSync(file, path.join(SITE_DIR, name));
    frames.push({ image: name, caption, cursor, focus, click: !!cursorTo, dwellMs });
  }

  const editor = () => page.locator('[data-tour="editor"]');
  const runPanel = () => page.locator('[data-tour="run"]');

  // 1 — workspace: the vulnerable runtime is loaded. Zoom the run panel; cursor → Exploit
  // (the button the viewer will "click" to start the attack — kept inside the zoomed region).
  await openLab(page, LAB, "learn");
  await expect(page.locator(".monaco-editor").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('[data-tour="invariants"] [data-state]').first()).toBeVisible();
  await shoot(
    "01-workspace.png",
    "This is DVAH-001. You harden the agent runtime — the harness. The exploit/patch/prove buttons grade you. Click Exploit to run the attack.",
    page.getByRole("button", { name: /exploit/i }),
    runPanel(),
    2600,
  );

  // 2 — exploit ran: board goes red (INV-01). Zoom the run panel + board; cursor → timeline tab.
  await runMarker(page, "exploit");
  await shoot(
    "02-exploit-red.png",
    "The exploit runs. DVAH-001 authorizes the plan once, then executes every step — so an unauthorized delete slips through. The board turns red: INV-01 (complete mediation) is broken.",
    page.getByRole("tab", { name: /agent timeline/i }),
    runPanel(),
    3200,
  );

  // 3 — trace: the agent timeline shows the unauthorized delete. Zoom the timeline; the cursor
  // highlights an `executed` row (kept inside the zoomed region).
  await page.getByRole("tab", { name: /agent timeline/i }).first().click();
  await expect(runPanel().getByText(/executed/i).first()).toBeVisible({ timeout: 20_000 });
  await shoot(
    "03-trace.png",
    "The trace shows exactly why: one authorization decision, but two executed actions — the delete was never authorized at the moment it ran.",
    runPanel().getByText(/executed/i).first(), // the timeline row, not the code
    runPanel(),
    3200,
  );

  // 4 — patched: the reference fix is in the editor. Zoom the editor; the cursor rests on the
  // patched code (kept inside the zoomed region).
  await page.getByRole("tab", { name: /^run$/i }).first().click();
  await applyFix(page, "guardrails/vulnerable/executor.py", FIXES[LAB]);
  await shoot(
    "04-patched.png",
    "The fix: authorize every resolved action the moment it runs — route each step through the harness's per-action gate. Now re-run everything.",
    page.locator(".monaco-editor").first(),
    editor(),
    2800,
  );

  // 5 — prove: re-run all tiers → green board + the two scores. Zoom the run panel. End frame.
  await runMarker(page, "run all");
  await page.waitForFunction(
    () => {
      const cells = Array.from(document.querySelectorAll('[data-tour="invariants"] [data-state]'));
      return cells.length > 0 && cells.every((c) => c.getAttribute("data-state") === "hold");
    },
    undefined,
    { timeout: 60_000 },
  );
  await shoot(
    "05-green.png",
    "Proven: the exploit and its mutated variants (delete → rename) are all denied — the invariant holds for every input. The board is green, and the two scores separate the runtime-security verdict from what the model did.",
    null,
    runPanel(),
    4000,
  );

  const states = await boardStates(page);
  if (!(states.length > 0 && states.every((s) => s === "hold"))) {
    throw new Error(`board not all-hold: ${states.join(",")}`);
  }

  // Manifest drives both the app /demo player and the static site/demo.html.
  const manifest = JSON.stringify(frames, null, 2);
  fs.writeFileSync(path.join(PUBLIC_DIR, "manifest.json"), manifest);
  fs.writeFileSync(path.join(SITE_DIR, "manifest.json"), manifest);

  // Drop any stale frames from earlier designs.
  for (const dir of [PUBLIC_DIR, SITE_DIR]) {
    for (const f of fs.readdirSync(dir)) {
      if (f.endsWith(".png") && !frames.some((fr) => fr.image === f)) fs.rmSync(path.join(dir, f));
    }
  }
});
