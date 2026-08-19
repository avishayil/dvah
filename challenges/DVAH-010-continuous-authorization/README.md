# DVAH-010 — Authority That Outlives You

**Broken invariant:** INV-09 — authority is re-validated for the lifetime of a running
action; a revocation must reach in-flight agents.

## The setup
`task-runner` may `files:read` and `files:delete`, but `files:delete` has been **revoked**
in the live revocation registry. A running task reads a scratch file (allowed) and then
tries to delete the production DB.

## The bug
`vulnerable/policy.py` (`CachingPolicy`) authorizes the **first** resolved action and then
reuses that decision for every later action — never re-checking the registry. Point-in-time
authorization means a revocation issued mid-run never takes effect.

## Your job
Authorize every resolved action freshly against the live `RevocationRegistry` so a revoked
action is denied with invariant `INV-09`. The reference fix wraps
`BuiltinPolicy(revocation=…)`.

## Prove it
```
dvah test DVAH-010
```
The exploit denies the revoked delete mid-run; the invariant test shows a revoked action
is denied regardless of how many actions were allowed before it; the adversarial test puts
the revoked action first, so a fix that only re-checks *later* actions still fails.
