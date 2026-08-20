# DVAH-002 — The Privileged Child

**Broken invariant:** INV-02 — a child's capabilities must be
`requested ∩ parent ∩ policy`; a child can never exceed its parent.

## The setup
`investigator` holds only `github:issue.read`. It delegates to `research-agent`,
requesting read + comment. The child role's policy profile permits read + comment.

## The bug
`vulnerable/capabilities.py` returns the **policy profile** for the child, ignoring
the parent entirely. The child ends up with `issue.comment` even though its parent
never had it, and posts a comment it should not be able to.

## Your job
Attenuate: `child = requested ∩ parent ∩ policy`. The reference fix is in `solution/`.

## Prove it
```
dvah test DVAH-002
```
The exploit test passes only when the child's out-of-scope comment is denied; the
invariant (property) test checks that for *any* inputs the derived child set is a
subset of both parent and policy.

## Artifacts
This lab ships an authored `agents/investigator.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
