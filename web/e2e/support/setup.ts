import { test as base, expect } from "@playwright/test";

// Shared fixture for every spec EXCEPT tour.spec: suppress the driver.js tour and the
// loop banner so their overlays don't intercept clicks in a fresh browser context.
// (tour.spec imports base `@playwright/test` so it can exercise the tour.)
export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(() => {
      try {
        const orig = Storage.prototype.getItem;
        // Any `dvah:tour:<name>:v1` reads as already-seen → no auto-start overlay.
        Storage.prototype.getItem = function (key: string) {
          if (typeof key === "string" && key.startsWith("dvah:tour:")) return "seen";
          return orig.call(this, key);
        };
        window.localStorage.setItem("dvah:loopbanner:dismissed", "1");
      } catch {
        /* environments without localStorage — ignore */
      }
    });
    await use(page);
  },
});

export { expect };
