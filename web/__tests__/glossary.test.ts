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

  it("defines the 2026 reference-architecture primitives", () => {
    for (const id of ["resource", "workflow", "guardrail", "prompt-layer"]) {
      const e = GLOSSARY[id];
      expect(e, id).toBeTruthy();
      expect(typeof e.term, `${id}.term`).toBe("string");
      expect(e.term.length, `${id}.term`).toBeGreaterThan(0);
      for (const f of ["short", "long", "example"] as const) {
        expect(typeof e[f], `${id}.${f}`).toBe("string");
        expect(e[f].length, `${id}.${f}`).toBeGreaterThan(10);
      }
    }
    // A resource is read-only data, treated as untrusted-by-default — not instructions.
    const resource = `${GLOSSARY["resource"].short} ${GLOSSARY["resource"].long}`.toLowerCase();
    expect(resource).toContain("untrusted");
    expect(resource).toContain("instruction");
    // A workflow distinguishes code-driven (deterministic) from LLM-driven orchestration.
    const workflow = `${GLOSSARY["workflow"].short} ${GLOSSARY["workflow"].long}`.toLowerCase();
    expect(workflow).toContain("code-driven");
    expect(workflow).toContain("llm-driven");
    // Guardrails are the swappable security-services layer enforced at the envelope gate.
    const guardrail = `${GLOSSARY["guardrail"].short} ${GLOSSARY["guardrail"].long}`.toLowerCase();
    expect(guardrail).toContain("security service");
    expect(guardrail).toContain("envelope");
    // Prompt layers replace one mega-prompt with ordered system→agent→skill→task layers.
    const promptLayer = `${GLOSSARY["prompt-layer"].short} ${GLOSSARY["prompt-layer"].long}`.toLowerCase();
    expect(promptLayer).toContain("system");
    expect(promptLayer).toContain("task");
  });
});
