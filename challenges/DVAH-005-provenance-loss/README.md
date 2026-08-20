# DVAH-005 — Who Told You That?

**Broken invariant:** INV-05 — provenance (source/trust/tenant/timestamp) is preserved
through every hop.

## The bug
`guardrails/vulnerable/provenance.py` drops the tag on `merge`, so after a tool call the agent no
longer knows where the data came from — any later policy decision that depends on
provenance is now blind.

## Your job
Preserve every provenance tag. The reference fix is in `guardrails/solution/`.

## Prove it
```
dvah test DVAH-005
```
Passes only when a tool result's source is still recorded after it flows back.

## Artifacts
This lab ships an authored `agents/investigator.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
