"""Canonical vulnerable implementations, one per invariant defeat.

These mirror the per-lab bugs but live here so the mutation engine is
scenario-independent (it does not import from ``challenges/``).
"""

from __future__ import annotations

from ..harness.compiler import DATA, INSTRUCTION, CompiledContext, ContextItem
from ..harness.resolver import build_envelope, resolve_operation
from ..models.approval import ApprovalGrant
from ..models.provenance import TrustLevel
from ..guardrails.decision import Decision, Denied, Verdict


class PlanTimeExecutor:
    """INV-01 defeat: authorize the first step once, then execute the rest raw.

    Emits ``executed`` trace events (but only one ``policy.decision``) so an
    execution-time-authorization probe can see actions that were never authorized.
    """

    def execute_plan(self, harness, ctx, steps):
        cfg = harness.cfg
        task = ctx.intent.task_id
        first_env = build_envelope(ctx, resolve_operation(steps[0]))
        decision = cfg.policy.authorize(first_env)
        cfg.trace.emit("policy.decision", task, first_env.action_hash,
                       action_id=first_env.action_id,
                       verdict=decision.verdict.value, invariant=decision.invariant,
                       reason="plan-time (once)")
        if decision.verdict is Verdict.DENY:
            raise Denied(decision)
        results = []
        for step in steps:
            op = resolve_operation(step)
            env = build_envelope(ctx, op)
            result = cfg.tools.invoke(op, cfg.secrets.resolve(op.namespace, op))
            cfg.trace.emit("executed", task, env.action_hash, action_id=env.action_id,
                           ok=result.ok)
            results.append(result)
        harness.last_ctx = ctx
        return results


class UnionCapabilityResolver:
    """INV-02 defeat: child inherits the full policy profile (no attenuation)."""

    def derive_child(self, requested, parent, policy):
        return policy


class PlanBoundApprovalService:
    """INV-03 defeat: approval binds to a constant 'plan id', not the action hash."""

    _PLAN_TOKEN = "sha256:plan-bound-token"

    def request(self, envelope) -> ApprovalGrant:
        return ApprovalGrant(approval_id="approval-plan", approved_action_hash=self._PLAN_TOKEN)

    def validate(self, envelope, grant) -> bool:
        return grant.approved_action_hash == self._PLAN_TOKEN

    def find(self, grants, envelope):
        return grants[0] if grants else None


class NoRedactSecretBroker:
    """INV-04 defeat: inject like the real broker, but never redact model context."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def resolve(self, namespace, operation):
        return self._inner.resolve(namespace, operation)

    def redact_for_model(self, context):
        return context


class DroppingProvenanceTracker:
    """INV-05 defeat: merge silently drops the tag; provenance is lost across hops."""

    def tag_tool_output(self, source, trust, tenant, timestamp):
        return None

    def merge(self, record, tag):
        return record

    def has_untrusted_instruction(self, record) -> bool:
        return False


class FlatteningContextCompiler:
    """INV-06 defeat: retrieved data is flattened into the instruction channel."""

    def compile(self, ctx) -> CompiledContext:
        items = [
            ContextItem(
                channel=INSTRUCTION,
                trust=TrustLevel.USER_INSTRUCTION,
                source="user",
                content={"text": ctx.intent.purpose},
            )
        ]
        for obs in ctx.observations:
            items.append(
                ContextItem(
                    channel=INSTRUCTION,  # BUG: untrusted data promoted to instruction
                    trust=obs.trust,
                    source=obs.source,
                    content=obs.content,
                )
            )
        return CompiledContext(items=tuple(items))


class PerAgentBudgetTracker:
    """INV-06 (budget) defeat: budget is per-agent, so delegation mints fresh budget."""

    def charge(self, ctx) -> None:
        if ctx.actions_used >= ctx.constraints.max_actions:
            raise Denied(
                Decision(verdict=Verdict.DENY, reason="per-agent budget", invariant="INV-06")
            )

    def remaining(self) -> int:
        return 1  # effectively unbounded across the tree


class ToolNamePolicy:
    """INV-13 defeat: authorize on the tool NAMESPACE only, not the operation."""

    def authorize(self, envelope) -> Decision:
        op = envelope.operation
        namespaces = {c.namespace for c in envelope.capabilities.caps}
        if op.namespace in namespaces:
            return Decision(verdict=Verdict.ALLOW, reason="tool namespace permitted")
        return Decision(
            verdict=Verdict.DENY, reason="namespace not permitted", invariant="INV-13"
        )


class NoAttributionPolicy:
    """INV-08 defeat: authorize without verifying attribution correspondence.

    Accepts whatever delegation chain the envelope carries (a forged root_principal
    or a chain tip that isn't the actor) as long as capabilities permit — the exact
    gap a truthiness-only attribution check leaves open.
    """

    def authorize(self, envelope) -> Decision:
        op = envelope.operation
        if not envelope.capabilities.permits(op.namespace, op.action):
            return Decision(
                verdict=Verdict.DENY,
                reason=f"no capability for {op.namespace}.{op.action}",
                invariant="INV-01",
            )
        return Decision(verdict=Verdict.ALLOW, reason="attribution not verified")


class AutoGrantSkillLoader:
    """INV-07 defeat: an upgraded skill's requested perms are granted wholesale."""

    def load(self, manifest, approved_permissions, pinned_digest):
        from ..models.capability import CapabilitySet
        from ..guardrails.skills import SkillLoadResult

        return SkillLoadResult(
            granted=CapabilitySet(caps=frozenset(manifest.permissions)),
            expanded=(),
            trusted=True,
        )


class CrossTenantMemoryProvider:
    """INV-10 defeat: memory leaks across tenants and is treated as instruction."""

    def __init__(self, store) -> None:
        self._store = store

    def recall(self, tenant, timestamp):
        items = []
        for owning_tenant, notes in self._store._by_tenant.items():  # BUG: all tenants
            for note in notes:
                items.append(
                    {
                        "trust": TrustLevel.USER_INSTRUCTION,  # BUG: memory as instruction
                        "tenant": owning_tenant,
                        "source": note["source"],
                        "content": note["content"],
                        "timestamp": timestamp,
                    }
                )
        return tuple(items)


class DigestBlindApprovalService:
    """INV-11 defeat: approval binds to the operation only, ignoring the tool digest."""

    def _blind(self, envelope) -> str:
        op = envelope.operation
        return f"{op.namespace}.{op.action}:{op.resource}:{op.parameters_hash}"

    def request(self, envelope) -> ApprovalGrant:
        return ApprovalGrant(approval_id="approval-blind", approved_action_hash=self._blind(envelope))

    def validate(self, envelope, grant) -> bool:
        return grant.approved_action_hash == self._blind(envelope)

    def find(self, grants, envelope):
        return grants[0] if grants else None


class RacyBudgetTracker:
    """INV-12 defeat: check-then-act with a gap, so interleaved charges race past the limit."""

    def __init__(self, limit: int = 1) -> None:
        self.limit = limit
        self.used = 0

    def check(self) -> bool:
        return self.used < self.limit

    def commit(self) -> None:
        self.used += 1

    def charge(self, ctx) -> None:  # normal (sequential) interface
        if self.used >= self.limit:
            raise Denied(Decision(verdict=Verdict.DENY, reason="budget", invariant="INV-12"))
        self.used += 1

    def remaining(self) -> int:
        return max(0, self.limit - self.used)
