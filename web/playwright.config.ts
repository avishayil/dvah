import { defineConfig, devices } from "@playwright/test";

// E2E is MANUAL / opt-in (run via `npm run e2e`); never part of `npm test` or the push/PR
// CI. The webServer entries reuse an already-running stack (e.g. `docker compose up`).
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  fullyParallel: false,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    // Chromium-based phone (Pixel 5) so no extra browser engine is needed — the
    // responsive check only cares about a mobile viewport, not the WebKit engine.
    { name: "mobile", use: { ...devices["Pixel 5"] } },
  ],
  webServer: [
    {
      command: ".venv/bin/python -m uvicorn dvah.webapi.app:app --port 8000",
      cwd: "..",
      url: "http://localhost:8000/api/challenges",
      reuseExistingServer: true,
      timeout: 60_000,
      env: { DVAH_CORS_ORIGINS: "http://localhost:3000" },
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
