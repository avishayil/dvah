"""AgentRuntime — delegation to model-backed subagents.

A ``delegate`` plan step spawns a subagent. This is where capability attenuation
(INV-02) and delegation-depth budget (INV-06) are enforced, BEFORE the child starts.
Requested and policy capabilities come from the step parameters (scenario-defined).

Since v0.3 the child is a real model session: it gets an attenuated ``RunContext``,
its own session identity, optionally its own attached skills, and then runs its OWN
turn loop via ``Harness.run_session`` (the same loop the root agent uses). In the
deterministic CI oracle the child session replays its ``subplan_task_id`` script, so
existing labs (DVAH-002/006) behave identically; a live child would react turn-by-turn.
The per-action ``run_step`` gate and the invariants are unchanged.
"""

from __future__ import annotations

from ..models.capability import Capability, CapabilitySet
from ..models.skill import SkillManifest
from ..providers.model import AgentState, PlanStep
from ..providers.session import ScriptedSession
from ..providers.tools import ToolResult
from ..guardrails.decision import Decision, Denied, Verdict
from .context import RunContext


def _cap_set(raw: list[dict] | None) -> CapabilitySet:
    return CapabilitySet(
        caps=frozenset(Capability(**c) for c in (raw or []))
    )


class AgentRuntime:
    def __init__(self, cfg: "HarnessConfig") -> None:  # noqa: F821
        self.cfg = cfg

    def delegate(self, harness: "Harness", ctx: RunContext, step: PlanStep) -> list[ToolResult]:  # noqa: F821
        cfg = self.cfg
        params = step.parameters
        child_id = params["child_agent_id"]
        requested = _cap_set(params.get("requested_capabilities"))
        policy_caps = _cap_set(params.get("policy_capabilities"))

        # INV-06: delegation depth budget.
        if ctx.delegation.depth + 1 > ctx.constraints.delegation_depth:
            raise Denied(Decision(verdict=Verdict.DENY,
                                  reason="delegation depth budget exceeded",
                                  invariant="INV-06"))

        # INV-02: child capabilities are attenuated, never widened.
        child_caps = cfg.capabilities.derive_child(requested, ctx.capabilities, policy_caps)
        cfg.trace.emit("delegate", ctx.intent.task_id, None,
                       child=child_id, child_caps=sorted(
                           f"{c.namespace}.{c.action}" for c in child_caps.caps))

        child_ctx = ctx.child(
            agent_id=child_id,
            instance_id=f"{child_id}-inst",
            capabilities=child_caps,
        )

        # Optional: attach the child's own skills (opt-in via the delegate step; no lab
        # declares this yet, so back-compat holds). A skill can never widen the child
        # beyond its attenuated caps (INV-07 + the intersection in attach_skill).
        for raw_skill in params.get("child_skills", []) or []:
            child_ctx, _ = harness.attach_skill(child_ctx, SkillManifest(**raw_skill))

        # The child is a distinct session with its own identity (its instance + chain
        # depth). Phase 6 promotes this to a full ModelIdentity on the envelope.
        subplan_task = params["subplan_task_id"]
        child_session_id = f"{child_id}@d{child_ctx.delegation.depth}"
        cfg.trace.emit(
            "subagent.started", ctx.intent.task_id, None,
            child=child_id, session_id=child_session_id, subplan=subplan_task,
            depth=child_ctx.delegation.depth,
        )

        # Run the child's OWN session loop (identical to run_task, but explicit as a
        # child sub-loop): the deterministic session replays subplan_task's script.
        child_session = ScriptedSession(cfg.model, subplan_task)
        return harness.run_session(child_ctx, child_session, AgentState(task_id=subplan_task))
