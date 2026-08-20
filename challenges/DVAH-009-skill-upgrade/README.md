# DVAH-009 — The Helpful Skill Update

**Broken invariant:** INV-07 — a skill upgrade cannot silently expand capabilities.

## The setup
A skill is a **runtime object** the agent loads: it contributes an instruction fragment
and tool schemas, and it *declares* the capabilities (and mcp/network/secrets) it needs
(see `dvah/models/skill.py`). Loading one is an explicit step —
`harness.attach_skill(ctx, skill, approved_permissions, pinned_digest)` — that runs the
`skill_loader` slot and, on a trusted load, injects the skill's instructions into the
compiled context (emitting a `skill.loaded` trace event).

The skills ship as real **`SKILL.md` files** (Anthropic Agent Skills shape: frontmatter
`name`/`description`/`version`/`digest`/`allowed-tools`/`requested-permissions` + a Markdown
body). `skills/registry.yaml` names which file plays each role: `approved` →
`skills/github-investigator/SKILL.md`, `upgrade` → `skills/github-investigator-upgrade/SKILL.md`,
`trojan` → `skills/github-investigator-trojan/SKILL.md`. The agent that loads them is defined
in `agents/skill-runner.md` (Claude Code subagent frontmatter + system prompt). The tests
read these manifests via `loaded.skills`.

Here the agent runs `github-investigator`, whose *approved* manifest (v1.2) permits only
`github:issue.read`, pinned to its digest. The "helpful" `upgrade` (v1.3) ships a manifest
with a NEW digest that also **requests** `github:issue.comment`; the adversarial `trojan`
keeps the approved digest but requests destructive powers
(`github:repository.delete` / `files:*`). Requesting is not granting — the loader decides.

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

## Artifacts
This lab ships the `skills/` package described above (`SKILL.md` files + `registry.yaml`), an
authored `agents/skill-runner.md` (its `AgentDefinition` — frontmatter + system prompt, with
`capabilities` cross-validated against `environment/agents.yaml`), and a `prompts/system.md`
base instruction layer. The skill manifests are load-bearing for this lab (the loader decides
what to grant); the agent/prompt overlays are advisory — nothing there reaches `action_hash`
or changes the security verdict.
