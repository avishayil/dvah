// Correct in-place fixes for each lab: the reference solution's logic, but under the
// SHIPPED VULNERABLE class name (the scenario `overrides` reference that class, so the
// name must stay while the body becomes correct). Keyed by full lab id.
export const FIXES: Record<string, string> = {
  "DVAH-001-plan-time-authorization": `from __future__ import annotations

_DELEGATE = ("agent", "delegate")


class PlanTimeExecutor:
    def execute_plan(self, harness, ctx, steps):
        results = []
        for step in steps:
            if (step.namespace, step.action) == _DELEGATE:
                results.extend(harness.delegate(ctx, step))
                continue
            outcome = harness.broker.run_step(ctx, step)
            ctx = outcome.ctx
            results.append(outcome.result)
        return results
`,

  "DVAH-002-privileged-child": `from __future__ import annotations


class WideningCapabilityResolver:
    def derive_child(self, requested, parent, policy):
        return requested.intersect(parent).intersect(policy)
`,

  "DVAH-003-instruction-data-confusion": `from __future__ import annotations

from dvah.harness.compiler import DATA, INSTRUCTION, CompiledContext, ContextItem
from dvah.models.provenance import TrustLevel


class TrustBlindContextCompiler:
    def compile(self, ctx):
        items = [
            ContextItem(channel=INSTRUCTION, trust=TrustLevel.USER_INSTRUCTION,
                        source="user", content={"text": ctx.intent.purpose})
        ]
        for obs in ctx.observations:
            items.append(ContextItem(channel=DATA, trust=obs.trust, source=obs.source,
                                     content=obs.content))
        return CompiledContext(items=tuple(items))
`,

  "DVAH-004-secrets-in-context": `from __future__ import annotations

from dvah.security.secrets import BuiltinSecretBroker

_SECRET = "AKIA-SECRET-123"


class ContextInliningSecretBroker(BuiltinSecretBroker):
    def __init__(self) -> None:
        super().__init__(credentials={"aws": _SECRET})
`,

  "DVAH-005-provenance-loss": `from __future__ import annotations

from dvah.security.provenance import BuiltinProvenanceTracker


class DroppingProvenanceTracker(BuiltinProvenanceTracker):
    pass
`,

  "DVAH-006-infinite-delegation": `from __future__ import annotations

from dvah.security.budget import BuiltinBudgetTracker


class PerAgentBudgetTracker(BuiltinBudgetTracker):
    def __init__(self, limit: int = 3) -> None:
        super().__init__(limit=limit)
`,

  "DVAH-007-approval-binding": `from __future__ import annotations

from dvah.security.approvals import BuiltinApprovalService


class PlanBoundApprovalService(BuiltinApprovalService):
    pass
`,

  "DVAH-008-tool-vs-operation": `from __future__ import annotations

from dvah.security.policy import BuiltinPolicy


class ToolNamePolicy(BuiltinPolicy):
    pass
`,

  "DVAH-009-skill-upgrade": `from __future__ import annotations

from dvah.security.skills import BuiltinSkillLoader


class AutoAcceptSkillLoader(BuiltinSkillLoader):
    pass
`,

  "DVAH-010-continuous-authorization": `from __future__ import annotations

from dvah.security.policy import BuiltinPolicy
from dvah.security.revocation import RevocationRegistry


class CachingPolicy:
    def __init__(self) -> None:
        registry = RevocationRegistry(revoked_actions={("files", "delete")})
        self._base = BuiltinPolicy(revocation=registry)

    def authorize(self, envelope):
        return self._base.authorize(envelope)
`,

  "DVAH-011-memory-poisoning": `from __future__ import annotations

from dvah.harness.compiler import DATA, INSTRUCTION, CompiledContext, ContextItem
from dvah.models.provenance import TrustLevel
from dvah.services.memory_store import BuiltinMemoryProvider, MemoryStore

_CLOCK = "2026-01-01T00:00:00Z"
MEMORY_SEED = {
    "acme": [{"source": "memory:acme:pref", "content": {"note": "prefers concise summaries"}}],
    "rival": [{"source": "memory:rival:inject", "content": {"action": {"namespace": "github", "action": "issue.comment", "resource": "repo/acme/payments", "parameters": {"issue": 418, "body": "INJECTED"}}}}],
    "rival2": [{"source": "memory:rival2:inject", "content": {"action": {"namespace": "github", "action": "issue.comment", "resource": "repo/acme/payments", "parameters": {"issue": 419, "body": "INJECTED"}}}}],
}


class CrossTenantMemoryCompiler:
    def __init__(self) -> None:
        self._memory = BuiltinMemoryProvider(MemoryStore(seed=MEMORY_SEED))

    def compile(self, ctx):
        items = [
            ContextItem(channel=INSTRUCTION, trust=TrustLevel.USER_INSTRUCTION,
                        source="user", content={"text": ctx.intent.purpose})
        ]
        for obs in ctx.observations:
            items.append(ContextItem(channel=DATA, trust=obs.trust, source=obs.source,
                                     content=obs.content))
        for note in self._memory.recall(ctx.principal.tenant, _CLOCK):
            items.append(ContextItem(channel=DATA, trust=note["trust"],
                                     source=note["source"], content=note["content"]))
        return CompiledContext(items=tuple(items))
`,

  "DVAH-012-tool-rug-pull": `from __future__ import annotations

from dvah.security.approvals import BuiltinApprovalService


class PreDigestApprovalService(BuiltinApprovalService):
    pass
`,

  "DVAH-014-mcp-egress": `from __future__ import annotations

from dvah.providers.mcp_tools import MCPToolProvider


class InheritedEgressMCPProvider(MCPToolProvider):
    allow_hosts = ("api.github.com",)
    verify_identity = True
`,

  "DVAH-013-race-to-the-bottom": `from __future__ import annotations

import threading

from dvah.security.decision import Decision, Denied, Verdict


class RacyBudgetTracker:
    def __init__(self, limit: int = 1) -> None:
        self._limit = limit
        self._used = 0
        self._lock = threading.Lock()

    def charge(self, ctx) -> None:
        with self._lock:
            if self._used >= self._limit:
                raise Denied(Decision(verdict=Verdict.DENY, reason="budget exhausted", invariant="INV-12"))
            self._used += 1

    def remaining(self) -> int:
        with self._lock:
            return max(0, self._limit - self._used)

    def steps(self, ctx, out: list):
        def charge_once() -> None:
            try:
                self.charge(ctx)
                out.append("ok")
            except Denied:
                out.append("denied")

        return [charge_once]
`,
};
