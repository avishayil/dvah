# DVAH-009 — The Helpful Skill Update

**Broken invariant:** INV-07 — a skill upgrade cannot silently expand capabilities.

## The setup
A skill is a **runtime object** the agent loads: it contributes an instruction fragment
and tool schemas, and it *declares* the capabilities (and mcp/network/secrets) it needs
(see `dvah/models/skill.py`). Loading one is an explicit step —
`harness.attach_skill(ctx, skill, approved_permissions, pinned_digest)` — that runs the
`skill_loader` slot and, on a trusted load, injects the skill's instructions into the
compiled context (emitting a `skill.loaded` trace event).

Here the agent runs `github-investigator`, whose *approved* manifest (v1.2) permits only
`github:issue.read`, pinned to its digest. The "helpful" upgrade (v1.3) ships a manifest
that also **requests** `github:issue.comment` (and, in the exploit variants,
`github:repository.delete` / `files:*`). Requesting is not granting — the loader decides.

## The bug
`vulnerable/skills.py` (`AutoAcceptSkillLoader`) grants **every** permission the upgraded
manifest requests — ignoring the pinned digest and skipping the permission diff. The
skill silently gains destructive capabilities its owner never approved.

## Your job
Grant `requested ∩ approved`, only when the manifest digest matches the pinned one, and
flag any requested permission beyond the approved set as `requires_reapproval`. The
reference fix is in `solution/` (the `BuiltinSkillLoader` behavior).

## Prove it
```
dvah test DVAH-009
```
The invariant test asserts, for *any* approved/requested pair, `granted ⊆ approved`; the
exploit and adversarial tests assert an upgraded manifest (even one that keeps the pinned
digest) can never widen the granted set without re-approval.
