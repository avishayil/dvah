"""ActionBroker — the single authorize/approve/execute gate.

This is the correct reference lifecycle. It authorizes the *resolved* action just
before execution (INV-01), binds approvals to the action hash (INV-03), injects
secrets at the tool layer (INV-04), and records provenance of the output (INV-05).
A vulnerable challenge typically bypasses this gate rather than editing it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.observation import Observation
from ..models.provenance import INSTRUCTION_TRUST_LEVELS, TrustLevel
from ..providers.model import PlanStep
from ..providers.tools import ToolResult
from ..guardrails.decision import Decision, Denied, Verdict
from .context import RunContext
from .resolver import build_envelope, resolve_operation


@dataclass(frozen=True)
class StepOutcome:
    ctx: RunContext
    result: ToolResult


class ActionBroker:
    def __init__(self, cfg: "HarnessConfig") -> None:  # noqa: F821 (avoid cycle)
        self.cfg = cfg

    def run_step(self, ctx: RunContext, step: PlanStep) -> StepOutcome:
        cfg = self.cfg
        task_id = ctx.intent.task_id

        # (1) resolve + (2) construct envelope from the RESOLVED action
        operation = resolve_operation(step)
        env = build_envelope(ctx, operation)
        aid = env.action_id  # occurrence identity — threaded onto every event (INV-01)
        cfg.trace.emit("envelope.built", task_id, env.action_hash, action_id=aid,
                       namespace=operation.namespace, action=operation.action,
                       resource=operation.resource)

        # (3) authorize the resolved action (INV-01, INV-08 attribution, INV-13 operation-granular)
        decision = cfg.policy.authorize(env)
        cfg.trace.emit("policy.decision", task_id, env.action_hash, action_id=aid,
                       verdict=decision.verdict.value, invariant=decision.invariant,
                       reason=decision.reason)
        if decision.verdict is Verdict.DENY:
            cfg.trace.emit("denied", task_id, env.action_hash, action_id=aid,
                           invariant=decision.invariant)
            raise Denied(decision)

        # (4) approval binds to the action hash (INV-03)
        grant = None
        if decision.verdict is Verdict.NEEDS_APPROVAL:
            grant = cfg.approvals.find(ctx.grants, env) or cfg.approvals.request(env)
            if not cfg.approvals.validate(env, grant):
                bad = Decision(verdict=Verdict.DENY,
                               reason="approval does not bind to this resolved action",
                               invariant="INV-03")
                cfg.trace.emit("denied", task_id, env.action_hash, action_id=aid,
                               invariant="INV-03")
                raise Denied(bad)
            cfg.trace.emit("approval.used", task_id, env.action_hash, action_id=aid,
                           approved_hash=grant.approved_action_hash,
                           namespace=operation.namespace, action=operation.action,
                           resource=operation.resource)
            env = env.with_approval(grant)
            ctx = ctx.with_grant(grant)

        # (5) resolve the credential as out-of-band tool-layer plumbing (INV-04) — it is
        # never written into the operation, so the executed action == the authorized one.
        credential = cfg.secrets.resolve(env.operation.namespace, env.operation)

        # (6) execute — charge the shared action budget first (INV-06 budget arm)
        cfg.budget.charge(ctx)
        result = cfg.tools.invoke(env.operation, credential)
        cfg.trace.emit("executed", task_id, env.action_hash, action_id=aid, ok=result.ok,
                       namespace=operation.namespace, action=operation.action)

        # A one-time approval authorizes exactly this one execution (INV-03): consume it so
        # a replay of the same resolved action cannot recycle the grant.
        if grant is not None and getattr(grant, "one_time", False):
            consume = getattr(cfg.approvals, "consume", None)
            if consume is not None:
                consume(grant)

        # (7) provenance of output flows back (INV-05) and becomes an observation.
        # INV-14: the HARNESS assigns trust at an external boundary — a tool/server does
        # not get to declare itself trusted. Anything crossing an external provider that
        # claims instruction-level trust is downgraded to untrusted data before it can
        # influence the model context.
        trust = result.trust
        # External-ness is a PER-NAMESPACE fact when a ToolRouter multiplexes providers
        # (native files = first-party, mcp = external), so ask the router which provider
        # actually handled this operation; fall back to the flat flag for plain providers.
        if hasattr(cfg.tools, "is_external_for"):
            is_external = cfg.tools.is_external_for(operation.namespace)
        else:
            is_external = getattr(cfg.tools, "is_external", False)
        if is_external and trust in INSTRUCTION_TRUST_LEVELS:
            trust = TrustLevel.UNTRUSTED_DATA
            cfg.trace.emit("boundary.trust_downgraded", task_id, env.action_hash,
                           action_id=aid, declared=result.trust.value,
                           assigned=trust.value, source=result.source)
        tag = cfg.provenance.tag_tool_output(
            result.source, trust, ctx.principal.tenant, cfg.clock
        )
        ctx = ctx.with_provenance(cfg.provenance.merge(ctx.provenance, tag))
        ctx = ctx.with_observation(
            Observation(source=result.source, trust=trust, content=result.output)
        )
        cfg.trace.emit(
            "provenance.recorded", task_id, env.action_hash, action_id=aid,
            sources=[t.source for t in ctx.provenance.data_sources],
            trusts=[t.trust.value for t in ctx.provenance.data_sources],
        )
        return StepOutcome(ctx=ctx.tick(), result=result)
