"""LoadedHarnessAdapter — grade a *loaded challenge* (possibly vulnerable) via the battery.

Unlike :class:`BuiltinAdapter` (which always wires the correct ``Builtin*`` components and
therefore always holds), this adapter sources the lab-overridable security components from a
challenge's actual loaded config (``loaded.harness.cfg``). So when a challenge overrides a
slot with a broken implementation, the corresponding invariant probe *breaks* — which is
exactly what an out-of-process grader wants to observe.

Harness-level invariants that no lab expresses as a single overridable slot the battery can
observe (attribution INV-08, external-boundary trust INV-14) are inherited unchanged from
:class:`BuiltinAdapter`. Coverage note: the battery catches vulnerabilities that live in the
policy / capabilities / approvals / secrets / skill_loader / budget / executor / compiler
slots; a few labs whose defect only manifests in the per-tier pytest tests (e.g. memory
poisoning via the compiler for INV-10, MCP egress for INV-14) are graded by the pytest path,
not this battery. See docs/CONFORMANCE.md.
"""

from __future__ import annotations

from ..models.capability import CapabilitySet
from ..models.provenance import INSTRUCTION_TRUST_LEVELS, TrustLevel
from ..models.runtime import Constraints
from ..observability.trace import TraceLog
from ..providers.native_tools import NativeToolProvider
from ..providers.reactive import ContextActionModel
from ..security.decision import Denied, Verdict
from ..services.memory import FileStore, GithubStore
from .adapter import CompiledView, MemoryItem, RunOutcome
from .builtin_adapter import BuiltinAdapter, _ctx


def _mk_budget(cfg, limit: int):
    """Rebuild the loaded budget class with the probe's limit (reflects a broken budget)."""
    try:
        return type(cfg.budget)(limit=limit)
    except Exception:
        return cfg.budget


class LoadedHarnessAdapter(BuiltinAdapter):
    """Wrap a loaded challenge; probes route through its (possibly-broken) components."""

    def __init__(self, loaded) -> None:
        self.name = "loaded"
        self._cfg = loaded.harness.cfg

    def run_plan(self, caps, scripts, task, max_actions) -> RunOutcome:
        constraints = Constraints(max_actions=max_actions, delegation_depth=3)
        trace = TraceLog()
        # Keep the challenge's policy/executor/capabilities/etc., but give the probe its own
        # canonical world (files/github seeds), scripted model, fresh trace + budget.
        cfg = self._cfg.with_slots(
            model=ContextActionModel(scripts or {}),
            tools=NativeToolProvider(
                files=FileStore({"/tmp/a": "1", "/tmp/b": "2"}),
                github=GithubStore({"repo/x": {"issues": [{"id": 1}]}}),
            ),
            executor=self._cfg.executor,
            trace=trace,
            constraints=constraints,
            budget=_mk_budget(self._cfg, max_actions),
        )
        from ..harness.loop import Harness

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
        return self._cfg.capabilities.derive_child(requested, parent, policy)

    def approve(self, action):
        return self._cfg.approvals.request(self._envelope(action))

    def validate(self, action, grant) -> bool:
        return self._cfg.approvals.validate(self._envelope(action), grant)

    def compile_context(self, purpose, observations, secrets=()) -> CompiledView:
        from dataclasses import replace

        from ..models.envelope import Intent
        from ..models.observation import Observation

        ctx = replace(
            _ctx(CapabilitySet(), Constraints()),
            intent=Intent(task_id="probe", purpose=purpose),
        )
        for obs in observations:
            ctx = ctx.with_observation(
                Observation(source=obs["source"], trust=TrustLevel(obs["trust"]),
                            content=obs["content"])
            )
        compiled = self._cfg.context_compiler.compile(ctx)
        # Redact with the challenge's secret broker (reflects a broken redactor, INV-04).
        try:
            broker = type(self._cfg.secrets)(credentials={f"s{i}": v for i, v in enumerate(secrets)})
        except Exception:
            broker = self._cfg.secrets
        model_ctx = broker.redact_for_model(compiled.to_model_context())
        return CompiledView(
            has_untrusted_instruction=compiled.has_untrusted_instruction(),
            text_blob=repr(model_ctx),
        )

    def authorize(self, caps, namespace, action, resource, revoked=frozenset()):
        from ..models.operation import Operation
        from ..harness.resolver import build_envelope
        from ..security.revocation import RevocationRegistry
        from .adapter import AdapterDecision

        policy = self._cfg.policy
        if revoked:
            reg = RevocationRegistry(revoked_actions=set(revoked))
            try:
                policy = type(self._cfg.policy)(revocation=reg)
            except Exception:
                policy = self._cfg.policy
        env = build_envelope(_ctx(caps, Constraints()),
                             Operation(namespace=namespace, action=action, resource=resource))
        decision = policy.authorize(env)
        return AdapterDecision(allow=decision.verdict is Verdict.ALLOW, invariant=decision.invariant)

    def skill_grant(self, approved, requested, manifest_digest, pinned_digest) -> CapabilitySet:
        from ..models.skill import SkillManifest

        manifest = SkillManifest(name="skill", digest=manifest_digest,
                                 permissions=tuple(requested.caps))
        return self._cfg.skill_loader.load(manifest, tuple(approved.caps), pinned_digest).granted

    def recall_memory(self, tenant) -> tuple[MemoryItem, ...]:
        items = self._cfg.memory.recall(tenant, self._cfg.clock)
        return tuple(
            MemoryItem(tenant=i["tenant"], source=i["source"],
                       is_instruction=i["trust"] in INSTRUCTION_TRUST_LEVELS)
            for i in items
        )

    def budget_used_racing(self, limit, concurrent) -> int:
        # Reflect the challenge's budget class under real contention (INV-12 / DVAH-013).
        import threading
        from concurrent.futures import ThreadPoolExecutor

        tracker = _mk_budget(self._cfg, limit)
        ctx = _ctx(CapabilitySet(), Constraints(max_actions=limit))
        barrier = threading.Barrier(concurrent)
        counter_lock = threading.Lock()
        used = 0

        def attempt() -> None:
            nonlocal used
            barrier.wait()
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
