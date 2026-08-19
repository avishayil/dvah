# DVAH-001 — Check Once, Execute Forever

**Broken invariant:** INV-01 — every external side effect must be authorized on the
*resolved* action, immediately before execution.

## The setup
`task-runner` holds only `files:read`. A plan reads `/tmp/file` (allowed) and then
deletes `/prod/customer.db` (which it has no capability to do).

## The bug
`vulnerable/executor.py` authorizes the **first** plan step once, then executes every
remaining step directly against the tools — bypassing the per-action gate. The delete
runs even though it would be denied if checked at execution time.

## Your job
Make the executor authorize each resolved action just before it executes. The
reference fix lives in `solution/` (route every step through `harness.broker.run_step`).

## Prove it
```
dvah test DVAH-001              # against your patched vulnerable/ code
dvah test DVAH-001 --adversarial
```
Exploit and invariant tests pass only when the delete is blocked at execution time and
`/prod/customer.db` survives.
