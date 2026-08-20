"""BuiltinAdapter — the DVAH builtin harness behind the ``HarnessAdapter`` protocol.

Reuses the real correct security components (BuiltinPolicy, BuiltinCapabilityResolver,
BuiltinApprovalService, …), so a passing conformance run proves DVAH's own harness holds
all invariants. This is the reference adapter other runtimes are compared against.
"""

from __future__ import annotations

from ..harness.compiler import BuiltinContextCompiler
from ..harness.config import HarnessConfig
from ..harness.context import RunContext
from ..harness.executor import BuiltinExecutor
from ..harness.loop import Harness
from ..harness.resolver import build_envelope
from ..models.capability import Capability, CapabilitySet
from ..models.envelope import Intent
from ..models.identity import Actor, DelegationChain, Principal
from ..models.observation import Observation
from ..models.operation import Operation
from ..models.provenance import INSTRUCTION_TRUST_LEVELS, TrustLevel
from ..models.runtime import Constraints, RuntimeContext, SkillRef
from ..models.skill import SkillManifest
from ..observability.trace import TraceLog
from ..providers.native_tools import NativeToolProvider
from ..providers.reactive import ContextActionModel
from ..guardrails.approvals import BuiltinApprovalService
from ..guardrails.budget import BuiltinBudgetTracker
from ..guardrails.capabilities import BuiltinCapabilityResolver
from ..guardrails.decision import Denied, Verdict
from ..guardrails.policy import BuiltinPolicy
from ..guardrails.provenance import BuiltinProvenanceTracker
from ..guardrails.revocation import RevocationRegistry
from ..guardrails.secrets import BuiltinSecretBroker
from ..guardrails.skills import BuiltinSkillLoader
from ..services.world_state import FileStore, GithubStore
from ..memory.store import BuiltinMemoryProvider, MemoryStore
from .adapter import ActionDescriptor, AdapterDecision, CompiledView, MemoryItem, RunOutcome

_CLOCK = "2026-01-01T00:00:00Z"


def _ctx(caps: CapabilitySet, constraints: Constraints, runtime: RuntimeContext | None = None) -> RunContext:
    return RunContext(
        principal=Principal(user="alice", tenant="acme"),
        actor=Actor(agent_id="agent", instance_id="agent-i"),
        delegation=DelegationChain(root_principal="alice", chain=("agent",), depth=0),
        intent=Intent(task_id="probe", purpose="probe"),
        capabilities=caps,
        constraints=constraints,
        runtime=runtime or RuntimeContext(model="deterministic"),
    )


class BuiltinAdapter:
    """Reference adapter wrapping DVAH's correct builtin harness."""

    name = "builtin"

    def run_plan(self, caps, scripts, task, max_actions) -> RunOutcome:
        constraints = Constraints(max_actions=max_actions, delegation_depth=3)
        files = FileStore({"/tmp/a": "1", "/tmp/b": "2"})
        github = GithubStore({"repo/x": {"issues": [{"id": 1}]}})
        trace = TraceLog()
        cfg = HarnessConfig(
            model=ContextActionModel(scripts or {}),
            policy=BuiltinPolicy(),
            approvals=BuiltinApprovalService(),
            capabilities=BuiltinCapabilityResolver(),
            provenance=BuiltinProvenanceTracker(),
            secrets=BuiltinSecretBroker(),
            tools=NativeToolProvider(files=files, github=github),
            executor=BuiltinExecutor(),
            trace=trace,
            constraints=constraints,
            context_compiler=BuiltinContextCompiler(),
            budget=BuiltinBudgetTracker(limit=max_actions),
        )
        harness = Harness(cfg)
        try:
            harness.run_task(_ctx(caps, constraints), task)
        except Denied:
            pass
        return RunOutcome(
            executed_hashes=tuple(trace.executed_hashes()),
            authorized_hashes=frozenset(trace.authorized_hashes()),
            executed_count=len(trace.of_kind("executed")),
            provenance_records=len(trace.of_kind("provenance.recorded")),
        )

    def derive_child(self, requested, parent, policy) -> CapabilitySet:
        return BuiltinCapabilityResolver().derive_child(requested, parent, policy)

    def approve(self, action: ActionDescriptor):
        return BuiltinApprovalService().request(self._envelope(action))

    def validate(self, action: ActionDescriptor, grant) -> bool:
        return BuiltinApprovalService().validate(self._envelope(action), grant)

    def compile_context(self, purpose, observations, secrets=()) -> CompiledView:
        from dataclasses import replace

        ctx = replace(_ctx(CapabilitySet(), Constraints()),
                      intent=Intent(task_id="probe", purpose=purpose))
        for obs in observations:
            ctx = ctx.with_observation(
                Observation(source=obs["source"], trust=TrustLevel(obs["trust"]),
                            content=obs["content"])
            )
        compiled = BuiltinContextCompiler().compile(ctx)
        broker = BuiltinSecretBroker(credentials={f"s{i}": v for i, v in enumerate(secrets)})
        model_ctx = broker.redact_for_model(compiled.to_model_context())
        return CompiledView(
            has_untrusted_instruction=compiled.has_untrusted_instruction(),
            text_blob=repr(model_ctx),
        )

    def authorize(self, caps, namespace, action, resource, revoked=frozenset()) -> AdapterDecision:
        reg = RevocationRegistry(revoked_actions=set(revoked)) if revoked else None
        env = build_envelope(_ctx(caps, Constraints()),
                             Operation(namespace=namespace, action=action, resource=resource))
        decision = BuiltinPolicy(revocation=reg).authorize(env)
        return AdapterDecision(allow=decision.verdict is Verdict.ALLOW, invariant=decision.invariant)

    def authorize_attribution(self, principal_user, root_principal, chain, actor_agent) -> AdapterDecision:
        chain = tuple(chain)
        # Forge the chain via model_construct so a mismatched root/actor reaches the policy
        # (a well-formed chain still passes the model validator, so mismatch is structural-valid).
        forged = DelegationChain.model_construct(
            root_principal=root_principal, chain=chain, depth=max(0, len(chain) - 1)
        )
        ctx = RunContext(
            principal=Principal(user=principal_user, tenant="acme"),
            actor=Actor(agent_id=actor_agent, instance_id=f"{actor_agent}-i"),
            delegation=forged,
            intent=Intent(task_id="probe", purpose="probe"),
            capabilities=CapabilitySet(caps=frozenset({Capability(namespace="files", action="read")})),
            constraints=Constraints(),
            runtime=RuntimeContext(model="deterministic"),
        )
        env = build_envelope(ctx, Operation(namespace="files", action="read", resource="/x"))
        decision = BuiltinPolicy().authorize(env)
        return AdapterDecision(allow=decision.verdict is Verdict.ALLOW, invariant=decision.invariant)

    def skill_grant(self, approved, requested, manifest_digest, pinned_digest) -> CapabilitySet:
        manifest = SkillManifest(name="skill", digest=manifest_digest,
                                 permissions=tuple(requested.caps))
        result = BuiltinSkillLoader().load(manifest, tuple(approved.caps), pinned_digest)
        return result.granted

    def recall_memory(self, tenant) -> tuple[MemoryItem, ...]:
        store = MemoryStore({
            "acme": [{"source": "note-acme", "content": {"text": "ours"}}],
            "evil": [{"source": "note-evil", "content": {"text": "pwn"}}],
        })
        items = BuiltinMemoryProvider(store).recall(tenant, _CLOCK)
        return tuple(
            MemoryItem(tenant=i["tenant"], source=i["source"],
                       is_instruction=i["trust"] in INSTRUCTION_TRUST_LEVELS)
            for i in items
        )

    def budget_used_racing(self, limit, concurrent) -> int:
        """Charge a shared limit from ``concurrent`` REAL threads that hit ``charge()``
        simultaneously (a barrier releases them together). Returns how many succeeded.
        With an atomic tracker this never exceeds ``limit``; a non-atomic check-then-act
        would let extra charges race past it.
        """
        import threading
        from concurrent.futures import ThreadPoolExecutor

        tracker = BuiltinBudgetTracker(limit=limit)
        ctx = _ctx(CapabilitySet(), Constraints(max_actions=limit))
        barrier = threading.Barrier(concurrent)
        counter_lock = threading.Lock()
        used = 0

        def attempt() -> None:
            nonlocal used
            barrier.wait()  # maximize contention: all threads charge at once
            try:
                tracker.charge(ctx)
            except Denied:
                return
            with counter_lock:
                used += 1

        with ThreadPoolExecutor(max_workers=concurrent) as pool:
            for f in [pool.submit(attempt) for _ in range(concurrent)]:
                f.result()
        return used

    def external_tool_trust(self, declared_trust: str) -> str:
        # Mirrors ActionBroker (INV-14): output crossing an external boundary that claims
        # instruction-level trust is assigned untrusted-data by the harness.
        from ..models.provenance import INSTRUCTION_TRUST_LEVELS, TrustLevel

        try:
            declared = TrustLevel(declared_trust)
        except ValueError:
            return TrustLevel.UNTRUSTED_DATA.value
        if declared in INSTRUCTION_TRUST_LEVELS:
            return TrustLevel.UNTRUSTED_DATA.value
        return declared.value

    def _envelope(self, action: ActionDescriptor):
        runtime = RuntimeContext(
            model="m",
            skill=SkillRef(name="tool", digest=action.tool_digest) if action.tool_digest else None,
        )
        ctx = RunContext(
            principal=Principal(user="alice", tenant=action.tenant),
            actor=Actor(agent_id=action.actor, instance_id=f"{action.actor}-i"),
            delegation=DelegationChain(root_principal="alice", chain=(action.actor,), depth=0),
            intent=Intent(task_id="probe", purpose="probe"),
            capabilities=CapabilitySet(),
            constraints=Constraints(),
            runtime=runtime,
        )
        return build_envelope(ctx, Operation(namespace=action.namespace, action=action.action,
                                             resource=action.resource, parameters=action.parameters))
