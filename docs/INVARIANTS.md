# DVAH Security Invariants (v0.3)

DVAH is organized around **invariants**, not vulnerability names, so it outlives any
single Top-10 revision. Each lab targets one **primary** invariant — but because the
vulnerable code usually removes a security *chokepoint*, breaking it realistically takes
several invariants down at once (e.g. a vulnerable executor that skips authorization also
skips approval, budget, and provenance). That's faithful to real systems. Your fix must
restore the primary property for *all* inputs, not just the demonstrated exploit.

| ID | Invariant | Owner module | Enforced at |
|----|-----------|--------------|-------------|
| INV-01 | Every external side effect is authorized on the **resolved** action, immediately before execution — enforced per **occurrence** (`action_id`), so one authorization licenses exactly one execution | `dvah/guardrails/policy.py` + `dvah/observability/trace.py` | broker step 3 |
| INV-02 | `child_caps ⊆ requested ∩ parent ∩ policy` | `dvah/guardrails/capabilities.py` | `derive_child` |
| INV-03 | Approval binds to the resolved `action_hash`, not the plan; a `one_time` grant authorizes exactly one execution (consumed after use), reusable grants otherwise | `dvah/guardrails/approvals.py` | `validate()`/`consume()` |
| INV-04 | Credentials never enter model context; injected at the tool layer | `dvah/guardrails/secrets.py` | broker step 5 |
| INV-05 | Provenance (source/trust/tenant/ts) is preserved through every hop | `dvah/guardrails/provenance.py` | `tag`/`merge` |
| INV-06 | Retrieved data cannot silently become privileged instructions / delegation cannot mint fresh budget | `dvah/harness/compiler.py`, `dvah/guardrails/budget.py` | context compile; delegation |
| INV-07 | A skill upgrade cannot silently expand capabilities | `dvah/guardrails/skills.py` (skill digest + permission-diff) | skill load |
| INV-08 | Every action is attributable to principal + agent + delegation chain + instance | `dvah/models/envelope.py` + policy | envelope construction |
| INV-09 | Per-action authorization freshness + revocation propagation: authority is re-checked before *every* action and a revocation takes effect on the next one | `dvah/guardrails/revocation.py` + `policy.py` | per-action authorize |
| INV-10 | Memory is tenant-scoped and informational — never cross-tenant, never a privileged instruction | `dvah/memory/store.py` + `harness/compiler.py` | context compile |
| INV-11 | Approval binds to the tool/skill definition (digest), not just the operation | `dvah/models/envelope.py` (`action_hash`) + `guardrails/approvals.py` | approval binding |
| INV-12 | Security decisions are atomic — no check-then-act race can bypass a limit | `dvah/harness/scheduler.py` + `guardrails/budget.py` | shared-limit charge |
| INV-13 | Authorization binds to the resolved operation, never the tool namespace | `dvah/guardrails/policy.py` | broker step 3 (capability check) |
| INV-14 | Runtime boundaries are contained — network egress + tool-server identity are enforced by the harness, not inherited; output crossing an external boundary is assigned trust, not believed | `dvah/providers/mcp_tools.py` + `harness/broker.py` | external tool boundary |

> **INV-06 in the conformance battery.** INV-06 has two distinct failure modes, so the
> conformance battery realizes it as two testable sub-invariants under the INV-06 umbrella:
> **INV-06-instr** (DVAH-003 — retrieved data cannot silently become instructions) and
> **INV-06-budget** (DVAH-006 — delegation cannot mint fresh budget). This is a battery-side
> split only; the `scenario.yaml` labels are unchanged (both labs still declare `INV-06`).

## The central principle

**Plans propose; `ActionEnvelope`s carry authority.** Every side-effectful operation
is resolved into one frozen envelope immediately before execution. Authorization,
approval, capability checks, provenance, and secrets all bind to that envelope — never
to the plan. `action_hash` is a sha256 over
`{actor, namespace, action, resource, parameters_hash, delegation, tenant}`.

## Lab → invariant map

| Lab | Title | Broken invariant |
|-----|-------|------------------|
| DVAH-001 | Check Once, Execute Forever | INV-01 |
| DVAH-002 | The Privileged Child | INV-02 |
| DVAH-003 | Data Becomes Instructions | INV-06 (instruction/data) |
| DVAH-004 | Context Full of Secrets | INV-04 |
| DVAH-005 | Who Told You That? | INV-05 |
| DVAH-006 | Infinite Delegation | INV-06 (budget) |
| DVAH-007 | You Approved What? | INV-03 |
| DVAH-008 | Same Tool, Different Operation | INV-13 (tool-vs-operation) |
| DVAH-009 | The Helpful Skill Update | INV-07 (skill capability stability) |
| DVAH-010 | Authority That Outlives You | INV-09 (continuous authz / revocation) |
| DVAH-011 | Memory Knows Best | INV-10 (memory isolation) |
| DVAH-012 | The Tool Rug-Pull | INV-11 (tool-definition binding) |
| DVAH-013 | Race to the Bottom | INV-12 (atomic decisions) |
| DVAH-014 | The Unbounded Tool Server | INV-14 (runtime boundary containment) |
