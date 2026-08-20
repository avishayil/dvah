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

## Artifacts
This lab ships an authored `agents/task-runner.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
