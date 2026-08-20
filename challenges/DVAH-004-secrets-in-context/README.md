# DVAH-004 — Context Full of Secrets

**Broken invariant:** INV-04 — credentials never enter model context; they are injected
at the tool layer only.

## The setup
The agent reads a file that happens to contain a credential, then that content is
compiled into the model's context.

## The bug
`guardrails/vulnerable/secrets.py` does not redact secrets from the compiled model context, so the
credential is handed straight to the model.

## Your job
Redact every secret value (anywhere, including nested) before the model sees it. The
reference fix is in `guardrails/solution/`.

## Prove it
```
dvah test DVAH-004
```
Passes only when the secret value never appears in the compiled model context.

## Artifacts
This lab ships an authored `agents/ops-agent.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
