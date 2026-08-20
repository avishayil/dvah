# DVAH-013 — Race to the Bottom

**Broken invariant:** INV-12 — security decisions must be atomic; no check-then-act race
can bypass a limit.

## The setup
A shared limit permits **one** action. Two agents attempt it "concurrently." DVAH models
the concurrency deterministically (no real threads) with `InterleavingScheduler`, which
forces the interleaving `check A → check B → commit A → commit B`.

## The bug
`guardrails/vulnerable/budget.py` (`RacyBudgetTracker`) checks the limit and commits the charge as
**two separate steps**. Interleaved, both agents' checks see room, so both commit — two
actions run under a limit of one. Classic TOCTOU.

## Your job
Make the charge **atomic**: check-and-increment in one indivisible operation, so the
second attempt sees the first's effect and is denied. The reference fix is in `guardrails/solution/`
(`AtomicBudgetTracker`, a single critical section).

## Prove it
```
dvah test DVAH-013
```
The exploit/invariant/adversarial tests pass only when no interleaving lets more charges
succeed than the limit allows.

## Artifacts
This lab ships an authored `agents/worker.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
