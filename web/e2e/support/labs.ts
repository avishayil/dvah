// The 14-lab matrix for the E2E suite. `id` is the full challenge dir id (the /labs route
// param). `fixPath` is the editable vulnerable file; the fix content lives in fixes.ts.
export type Lab = {
  id: string;
  title: string;
  invariants: string[];
  fixPath: string;
};

export const LABS: Lab[] = [
  { id: "DVAH-001-plan-time-authorization", title: "Check Once, Execute Forever", invariants: ["INV-01"], fixPath: "guardrails/vulnerable/executor.py" },
  { id: "DVAH-002-privileged-child", title: "The Privileged Child", invariants: ["INV-02"], fixPath: "guardrails/vulnerable/capabilities.py" },
  { id: "DVAH-003-instruction-data-confusion", title: "Data Becomes Instructions", invariants: ["INV-06-instr"], fixPath: "guardrails/vulnerable/compiler.py" },
  { id: "DVAH-004-secrets-in-context", title: "Context Full of Secrets", invariants: ["INV-04"], fixPath: "guardrails/vulnerable/secrets.py" },
  { id: "DVAH-005-provenance-loss", title: "Who Told You That?", invariants: ["INV-05"], fixPath: "guardrails/vulnerable/provenance.py" },
  { id: "DVAH-006-infinite-delegation", title: "Infinite Delegation", invariants: ["INV-06-budget"], fixPath: "guardrails/vulnerable/budget.py" },
  { id: "DVAH-007-approval-binding", title: "You Approved What?", invariants: ["INV-03"], fixPath: "guardrails/vulnerable/approvals.py" },
  { id: "DVAH-008-tool-vs-operation", title: "Same Tool, Different Operation", invariants: ["INV-13"], fixPath: "guardrails/vulnerable/policy.py" },
  { id: "DVAH-009-skill-upgrade", title: "The Helpful Skill Update", invariants: ["INV-07"], fixPath: "guardrails/vulnerable/skills.py" },
  { id: "DVAH-010-continuous-authorization", title: "Authority That Outlives You", invariants: ["INV-09"], fixPath: "guardrails/vulnerable/policy.py" },
  { id: "DVAH-011-memory-poisoning", title: "Memory Knows Best", invariants: ["INV-10"], fixPath: "guardrails/vulnerable/compiler.py" },
  { id: "DVAH-012-tool-rug-pull", title: "The Tool Rug-Pull", invariants: ["INV-11"], fixPath: "guardrails/vulnerable/approvals.py" },
  { id: "DVAH-013-race-to-the-bottom", title: "Race to the Bottom", invariants: ["INV-12"], fixPath: "guardrails/vulnerable/budget.py" },
  { id: "DVAH-014-mcp-egress", title: "The Unbounded Tool Server", invariants: ["INV-14"], fixPath: "guardrails/vulnerable/mcp.py" },
];
