# DVAH-007 — You Approved What?

**Broken invariant:** INV-03 — approval binds to the resolved `action_hash`, not the
plan.

## The bug
`guardrails/vulnerable/approvals.py` issues a grant bound to a constant "plan id" and validates
any grant regardless of the action. An approval obtained for deleting `/tmp/old.log`
is then reused to authorize deleting `/prod/customer.db`.

## Your job
Bind each approval to the exact resolved action. The reference fix is in `guardrails/solution/`.

## Prove it
```
dvah test DVAH-007
```
Passes only when the approval that authorizes each action is bound to that action's own
hash — a stale, mismatched approval must never authorize a different action.

## Artifacts
This lab ships an authored `agents/ops-agent.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
