# Agent Harness Security Conformance

DVAH's invariants (INV-01…12) are not specific to *its* harness — they are properties any
agent runtime should hold. The **conformance suite** lifts the invariant checks behind a
runtime-agnostic `HarnessAdapter` so the same battery can probe **any** runtime: DVAH's
builtin harness, or an external one (LangGraph, CrewAI, an MCP server) via a thin shim.

> In the reference-architecture overlay (`docs/ARCHITECTURE.md`), the conformance battery and
> the per-lab test suites are DVAH's realization of the cross-cutting **Evals** layer — the
> repeatable, runtime-agnostic checks that a runtime holds its security invariants.

> **Scope, honestly.** By default the adapter *reports its own observables* (executed hashes,
> provenance counts, compiled-context flags), so a plain external result is **self-attestation**,
> not independent certification — a dishonest or buggy adapter can report a pass it didn't
> earn. Treat default external-adapter output as a **diagnostic**, not a certificate.
>
> **Grader-observed mode (`--observed`) closes that gap for the observable invariants.** DVAH's
> own mock services (`services/{files,github,email,cloud}`) now keep an authoritative
> side-effect recorder exposed at `GET /_recorder` (cleared by `POST /_reset`). When side
> effects flow through these DVAH-controlled services, the grader reads what *actually*
> happened and reconciles it against what the adapter *claims* it executed
> (`dvah/conformance/observed.py`). A claim with no matching recorded side effect — or a
> recorded side effect the adapter didn't own — **fails**, so a liar can no longer attest an
> observable pass. Run `dvah conformance --observed` with the services up
> (`docker compose --profile services up`); the purely-computed invariants (e.g. capability
> attenuation) remain self-reported by nature.
>
> One place the battery never takes the adapter's word: **INV-12 is a real race.**
> `budget_used_racing` now launches concurrent threads that hit the shared limit
> simultaneously (via a barrier), so a non-atomic check-then-act tracker actually
> over-charges and fails — it is no longer a sequential loop that a broken tracker could
> pass.

```
              Invariant battery (INV-01..12)
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
  BuiltinAdapter   ExternalHarness   <your runtime>
  (DVAH harness)   (reference mock)   (your adapter)
```

## Run it

```bash
uv run dvah conformance --adapter builtin      # DVAH's harness → all 13 hold, exit 0
uv run dvah conformance --adapter external     # reference mock → INV-01 & INV-11 fail, exit 1
uv run dvah conformance --adapter builtin --json   # machine-readable
```

## The `HarnessAdapter` contract

An adapter exposes the minimal security surface each invariant probe needs. The battery
holds the assertions; the adapter only performs neutral operations and returns
observables (`dvah/conformance/adapter.py`):

| Method | Invariants | What it must do |
|--------|-----------|-----------------|
| `run_plan(caps, scripts, task, max_actions)` | INV-01, INV-05, INV-06-budget | run a plan; report executed vs execution-time-authorized action hashes, executed count, provenance records |
| `derive_child(requested, parent, policy)` | INV-02 | return the child's effective capabilities |
| `approve(action)` / `validate(action, grant)` | INV-03, INV-11 | issue an approval bound to the resolved action **incl. the tool digest** |
| `compile_context(purpose, observations, secrets)` | INV-04, INV-06-instr | assemble model context; keep untrusted data out of the instruction channel and secrets out entirely |
| `authorize(caps, ns, action, resource, revoked)` | INV-13, INV-09 | authorize the specific operation; deny revoked authority |
| `skill_grant(approved, requested, manifest_digest, pinned_digest)` | INV-07 | grant only what the pinned/approved manifest allows |
| `recall_memory(tenant)` | INV-10 | return only the tenant's memory, informational (never instruction) |
| `budget_used_racing(limit, concurrent)` | INV-12 | charge a shared limit atomically (no check-then-act race) |

## Writing an adapter

Implement the protocol against your runtime's primitives and pass an instance to
`run_battery(adapter)` (`dvah/conformance/battery.py`). See
`dvah/conformance/external_adapter.py` for a ~60-line reference mock. A probe that raises
counts as a failed invariant, so partial/unsupported implementations surface as `✗`.

## Relationship to `dvah mutate`

`dvah mutate` is the adversarial sibling: it runs the equivalent invariant checks against
a DVAH harness with a hidden **defeat** injected, and asks you to diagnose which invariant
broke. Conformance runs the same invariant set against a *real* adapter to diagnose it. One
is a teaching game against a broken harness; the other is a self-attested diagnostic against
a real one (see the scope note above).
