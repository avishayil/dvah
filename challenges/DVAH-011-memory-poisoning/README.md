# DVAH-011 — Memory Knows Best

**Broken invariant:** INV-10 — memory is tenant-scoped and informational; never
cross-tenant, never a privileged instruction.

## The setup
The agent recalls "memory" into its context before acting. Tenant `acme`'s memory holds a
benign preference. Two *other* tenants (`rival`, `rival2`) have planted notes that embed
an action ("comment X on issue Y").

## The bug
`vulnerable/compiler.py` (`CrossTenantMemoryCompiler`) recalls **every** tenant's memory
and drops it into the **instruction** channel. The reactive model then obeys the planted
action — cross-tenant memory poisoning.

## Your job
Recall only the *current* tenant's memory, and place it in the **data** channel tagged
`TrustLevel.MEMORY` (informational, never an instruction). The reference fix uses
`BuiltinMemoryProvider`.

## Prove it
```
dvah test DVAH-011
```
Exploit: the planted cross-tenant action must never execute and the compiled context must
carry no untrusted instruction. Invariant/adversarial: memory items are always
data-channel and no foreign tenant's memory (`rival`, `rival2`) appears.

## Artifacts
This lab ships an authored `agents/assistant.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
