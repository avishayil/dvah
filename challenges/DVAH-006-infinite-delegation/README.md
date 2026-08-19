# DVAH-006 — Infinite Delegation

**Broken invariant:** INV-06 (budget arm) — delegation cannot mint fresh budget; one
shared budget bounds the whole delegation tree.

## The bug
`vulnerable/budget.py` keys the budget on a per-agent counter, which resets on every
delegation. An agent can run unbounded work by spawning subagents, each handed a fresh
allowance.

## Your job
Enforce a single shared, decrementing budget across the entire delegation tree. The
reference fix is in `solution/`.

## Prove it
```
dvah test DVAH-006
```
The global budget is 3 actions; the exploit plan tries to run 6 across a chain of
delegations. Passes only when the run is stopped at the budget and ≤3 actions execute.
