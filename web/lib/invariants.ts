// Canonical invariant statements (mirror of docs/INVARIANTS.md) for offline reference UI.
export const INVARIANTS: { id: string; statement: string }[] = [
  { id: "INV-01", statement: "Every external side effect is authorized on the resolved action, immediately before execution." },
  { id: "INV-02", statement: "Child capabilities ⊆ requested ∩ parent ∩ policy." },
  { id: "INV-03", statement: "Approval binds to the resolved action hash, not the plan." },
  { id: "INV-04", statement: "Credentials never enter model context; injected at the tool layer." },
  { id: "INV-05", statement: "Provenance is preserved through every hop." },
  { id: "INV-06", statement: "Retrieved data cannot silently become privileged instructions; delegation cannot mint fresh budget." },
  { id: "INV-06-instr", statement: "Retrieved data cannot silently become privileged instructions." },
  { id: "INV-06-budget", statement: "Delegation cannot mint fresh budget." },
  { id: "INV-07", statement: "A skill upgrade cannot silently expand capabilities." },
  { id: "INV-08", statement: "Every action is attributable to principal + agent + delegation chain + instance." },
  { id: "INV-09", statement: "Per-action authorization freshness + revocation propagation: authority is re-checked before every action and a revocation takes effect on the next one." },
  { id: "INV-10", statement: "Memory is tenant-scoped and informational — never cross-tenant, never a privileged instruction." },
  { id: "INV-11", statement: "Approval binds to the tool/skill definition (digest), not just the operation." },
  { id: "INV-12", statement: "Security decisions are atomic — no check-then-act race can bypass a limit." },
  { id: "INV-13", statement: "Authorization binds to the resolved operation, never the tool namespace." },
  { id: "INV-14", statement: "Runtime boundaries are contained — network egress and tool-server identity are enforced by the harness, not inherited." },
];

export const INVARIANT_MAP: Record<string, string> = Object.fromEntries(
  INVARIANTS.map((i) => [i.id, i.statement]),
);
