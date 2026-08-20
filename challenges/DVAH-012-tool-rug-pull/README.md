# DVAH-012 — The Tool Rug-Pull

**Broken invariant:** INV-11 — approval must bind to the tool/skill *definition* (its
digest), not merely to the operation.

## The setup
A human approves an action performed via a specific tool/skill (digest `D1`). Later the
tool's definition is swapped (digest `D2`) — same operation name, different code behind
it. This is the "rug-pull" at the heart of MCP tool-poisoning.

## The bug
`vulnerable/approvals.py` (`PreDigestApprovalService`) computes its approval binding over
the operation only, **omitting the tool digest**. So a grant issued for `D1` still
validates the identical operation now backed by `D2` — the user approved one tool and got
another.

## Your job
Bind approval to the resolved `action_hash`, which (since Wave A) already includes
`runtime.skill.digest` / `runtime.mcp_server.digest`. The reference fix is in `solution/`
(`FixedApprovalService` = the built-in, digest-bound approval service).

## Prove it
```
dvah test DVAH-012
```
The exploit and invariant tests pass only when a grant for `D1` refuses to validate the
same operation under a different tool digest `D2`.

## Artifacts
This lab ships an authored `agents/tool-user.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
