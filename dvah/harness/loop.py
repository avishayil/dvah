"""Harness — the top-level driver that ties the config together.

``run_task`` fetches a plan from the model provider and hands it to the (swappable)
executor. Delegation recurses back through ``run_task`` so subagents reuse the same
executor slot and gate.
"""

from __future__ import annotations

from ..models.capability import Capability
from ..models.skill import SkillManifest
from ..providers.model import AgentState, ModelRequest, ModelSession, PlanStep
from ..providers.session import ScriptedSession
from ..providers.tools import ToolResult
from ..security.skills import SkillLoadResult
from .agent import AgentRuntime
from .broker import ActionBroker
from .config import HarnessConfig
from .context import RunContext


class Harness:
    def __init__(self, cfg: HarnessConfig) -> None:
        self.cfg = cfg
        self.broker = ActionBroker(cfg)
        self.agent = AgentRuntime(cfg)
        #: Set by the executor for tests/tracing; not part of the security path.
        self.last_ctx: RunContext | None = None
        self.last_compiled = None

    def run_plan(self, ctx: RunContext, steps: tuple[PlanStep, ...]) -> list[ToolResult]:
        return self.cfg.executor.execute_plan(self, ctx, steps)

    def run_task(self, ctx: RunContext, task_id: str) -> list[ToolResult]:
        """Drive a model session for ``task_id``. The deterministic session replays
        the scripted plan (CI oracle); a live session would react turn-by-turn."""
        session = ScriptedSession(self.cfg.model, task_id)
        return self.run_session(ctx, session, AgentState(task_id=task_id))

    def run_session(
        self,
        ctx: RunContext,
        session: ModelSession,
        state: AgentState | None = None,
        prompt: str = "",
    ) -> list[ToolResult]:
        """The agent loop: ask the session for a turn, run each proposed tool call
        through the executor slot (which routes it through the per-action gate), then
        ask for the next turn until the session finishes or the action budget runs out.

        Per-turn steps still flow through ``cfg.executor`` so a swapped-in vulnerable
        executor (DVAH-001) is exercised and the ``run_step`` gate is unchanged."""
        state = state or AgentState(task_id=ctx.intent.task_id)
        tid = state.task_id
        results: list[ToolResult] = []
        # Agent-timeline events (v0.3): informational only — they carry no action_hash,
        # so INV-01 occurrence accounting (which keys on executed/policy.decision) is
        # unaffected.
        self.cfg.trace.emit("user.task", tid, None, prompt=prompt or "")
        while True:
            self.cfg.trace.emit("model.request", tid, None, turn=state.turns)
            turn = session.next((), (), state)
            self.cfg.trace.emit(
                "model.response", tid, None,
                turn=state.turns,
                tool_calls=len(turn.tool_calls),
                final=turn.final,
                model_identity=turn.model_identity,
                text=turn.text,
            )
            if turn.tool_calls:
                for call in turn.tool_calls:
                    self.cfg.trace.emit(
                        "tool.proposed", tid, None,
                        namespace=call.namespace, action=call.action, resource=call.resource,
                    )
                steps = tuple(call.to_plan_step() for call in turn.tool_calls)
                step_results = self.run_plan(ctx, steps)
                results.extend(step_results)
                for r in step_results:
                    self.cfg.trace.emit(
                        "observation.received", tid, None, ok=r.ok, source=r.source,
                    )
                if self.last_ctx is not None:
                    ctx = self.last_ctx  # thread the executor-advanced context forward
            state = state.model_copy(update={"turns": state.turns + 1})
            if turn.final:
                break
            if ctx.actions_used >= ctx.constraints.max_actions:
                break
        self.cfg.trace.emit(
            "agent.finished", tid, None, turns=state.turns, results=len(results),
        )
        return results

    def attach_skill(
        self,
        ctx: RunContext,
        skill: SkillManifest,
        approved_permissions: tuple[Capability, ...] | None = None,
        pinned_digest: str | None = None,
    ) -> tuple[RunContext, SkillLoadResult]:
        """Load a skill onto an agent (INV-07). The skill *requests* capabilities; the
        loader grants only ``requested ∩ approved`` and only when the digest is pinned —
        so requesting is never granting. The effective set is further bounded by the
        agent's own caps (a skill can never widen its host agent). A trusted load attaches
        the skill so the compiler injects its instruction fragment + tool schemas; an
        expanded/untrusted upgrade is flagged ``requires_reapproval`` and NOT attached.

        Opt-in: nothing calls this unless a lab/world declares a skill, so the 13
        non-skill labs are unaffected. The ``run_step`` gate is unchanged — a skill's
        granted caps still face the policy at execution time.
        """
        approved = approved_permissions if approved_permissions is not None else tuple(
            ctx.capabilities.caps
        )
        result = self.cfg.skill_loader.load(skill, approved, pinned_digest)
        # Belt-and-suspenders: a skill can never operate beyond its host agent's caps.
        effective = result.granted.intersect(ctx.capabilities)
        new_ctx = ctx
        if result.trusted and not result.requires_reapproval:
            new_ctx = ctx.with_skill(skill)
        self.cfg.trace.emit(
            "skill.loaded",
            ctx.intent.task_id,
            None,
            skill=skill.name,
            version=skill.version,
            granted=sorted(f"{c.namespace}.{c.action}" for c in effective.caps),
            expanded=[f"{c.namespace}.{c.action}" for c in result.expanded],
            trusted=result.trusted,
            requires_reapproval=result.requires_reapproval,
        )
        return new_ctx, result

    def delegate(self, ctx: RunContext, step: PlanStep) -> list[ToolResult]:
        return self.agent.delegate(self, ctx, step)

    def compile_context(self, ctx: RunContext) -> tuple[dict, ...]:
        """Compile the model's context from observations and redact secrets (INV-04/06)."""
        compiled = self.cfg.context_compiler.compile(ctx)
        self.last_compiled = compiled
        model_ctx = self.cfg.secrets.redact_for_model(compiled.to_model_context())
        self.cfg.trace.emit(
            "context.compiled", ctx.intent.task_id, None,
            untrusted_instruction=compiled.has_untrusted_instruction(),
        )
        return model_ctx

    def reflect(self, ctx: RunContext, step: PlanStep) -> list[ToolResult]:
        model_ctx = self.compile_context(ctx)
        response = self.cfg.model.complete(
            ModelRequest(task_id=step.parameters["followup_task_id"], context=model_ctx)
        )
        return self.run_plan(ctx, response.plan)
