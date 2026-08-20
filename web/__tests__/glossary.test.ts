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

  it("defines the file-based artifact terms (skill, tool-definition)", () => {
    for (const id of ["skill", "tool-definition"]) {
      const e = GLOSSARY[id];
      expect(e, id).toBeTruthy();
      expect(typeof e.term, `${id}.term`).toBe("string");
      expect(e.term.length, `${id}.term`).toBeGreaterThan(0);
      for (const f of ["short", "long", "example"] as const) {
        expect(typeof e[f], `${id}.${f}`).toBe("string");
        expect(e[f].length, `${id}.${f}`).toBeGreaterThan(10);
      }
    }
    // The load-bearing teaching: requesting a permission is not being granted it.
    const skill = GLOSSARY["skill"];
    expect(`${skill.short} ${skill.long}`.toLowerCase()).toContain("grant");
    expect(GLOSSARY["skill"].long).toContain("SKILL.md");
    // Tool definitions are advisory metadata, never authorization.
    expect(GLOSSARY["tool-definition"].long.toLowerCase()).toContain("advisory");
  });
});
