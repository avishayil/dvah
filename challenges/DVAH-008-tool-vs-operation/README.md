# DVAH-008 — Same Tool, Different Operation

**Broken invariant:** INV-13 / tool-vs-operation — authorize the specific operation,
not the tool name.

## The bug
`vulnerable/policy.py` authorizes on the operation **namespace**: if the agent holds
any `github` capability at all, every `github` operation is allowed. An agent with only
`github:issue.read` can therefore delete a repository.

## Your job
Authorize the specific operation against the exact capability held. The reference fix is
in `solution/`.

## Prove it
```
dvah test DVAH-008
```
Passes only when `repository.delete` is denied for an agent that holds only
`issue.read`, and the repository survives.

## Artifacts
This lab ships an authored `agents/reporter.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
