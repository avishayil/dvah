import { describe, it, expect } from "vitest";
import { GLOSSARY } from "@/lib/glossary";

describe("glossary entry-level terms", () => {
  it("defines 'harness' at entry level with the key fields", () => {
    const h = GLOSSARY["harness"];
    expect(h).toBeTruthy();
    expect(h.term.toLowerCase()).toContain("harness");
    for (const f of ["short", "long", "example"] as const) {
      expect(typeof h[f]).toBe("string");
      expect(h[f].length).toBeGreaterThan(10);
    }
    // The core teaching sentence should be present.
    expect(`${h.short} ${h.long}`.toLowerCase()).toContain("propos");
  });

  it("adds the supporting beginner terms", () => {
    for (const id of ["tool", "mcp", "model-session"]) {
      expect(GLOSSARY[id], id).toBeTruthy();
      expect(GLOSSARY[id].short.length).toBeGreaterThan(10);
    }
  });
});
