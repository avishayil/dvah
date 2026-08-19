"""The ``HarnessAdapter`` protocol — the runtime-agnostic security surface probed.

An adapter exposes the minimal set of security operations the invariant battery needs.
Anything that can implement these (DVAH's builtin harness, or an external runtime via a
thin shim) can be graded against INV-01…12. The battery holds the assertions; adapters
only perform the neutral operations and return observables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..models.capability import CapabilitySet


@dataclass(frozen=True)
class RunOutcome:
    """Result of running a plan: what executed vs what was authorized at exec time."""

    executed_hashes: tuple[str, ...]
    authorized_hashes: frozenset[str]
    executed_count: int
    provenance_records: int = 0


@dataclass(frozen=True)
class CompiledView:
    """A runtime-agnostic view of a compiled model context."""

    has_untrusted_instruction: bool
    text_blob: str  # concatenation of all context content, for leak checks


@dataclass(frozen=True)
class AdapterDecision:
    allow: bool
    invariant: str | None = None


@dataclass(frozen=True)
class MemoryItem:
    tenant: str
    source: str
    is_instruction: bool  # True if placed in the instruction channel (a violation)


@dataclass(frozen=True)
class ActionDescriptor:
    """A runtime-agnostic description of an action, for approval binding checks."""

    actor: str
    namespace: str
    action: str
    resource: str
    parameters: dict = field(default_factory=dict)
    tenant: str = "acme"
    tool_digest: str | None = None


@runtime_checkable
class HarnessAdapter(Protocol):
    name: str

    # INV-01 / INV-05 / INV-06-budget — run a plan, report exec-time authorization.
    def run_plan(
        self, caps: CapabilitySet, scripts: dict, task: str, max_actions: int
    ) -> RunOutcome: ...

    # INV-02 — delegation attenuation.
    def derive_child(
        self, requested: CapabilitySet, parent: CapabilitySet, policy: CapabilitySet
    ) -> CapabilitySet: ...

    # INV-03 / INV-11 — approval binding (to the resolved action, incl. tool digest).
    def approve(self, action: ActionDescriptor) -> object: ...
    def validate(self, action: ActionDescriptor, grant: object) -> bool: ...

    # INV-04 / INV-06-instr — context compilation. ``secrets`` are values that must be
    # redacted from the model-visible context (INV-04).
    def compile_context(
        self, purpose: str, observations: tuple[dict, ...], secrets: tuple[str, ...] = ()
    ) -> CompiledView: ...

    # INV-13 / INV-09 — per-operation authorization + revocation.
    def authorize(
        self,
        caps: CapabilitySet,
        namespace: str,
        action: str,
        resource: str,
        revoked: frozenset[tuple[str, str]] = frozenset(),
    ) -> AdapterDecision: ...

    # INV-08 — attribution must correspond to the principal + acting agent, not merely
    # be present. A forged root_principal or chain tip (that isn't the actor) is denied.
    def authorize_attribution(
        self,
        principal_user: str,
        root_principal: str,
        chain: tuple[str, ...],
        actor_agent: str,
    ) -> AdapterDecision: ...

    # INV-07 — skill upgrade cannot widen capabilities.
    def skill_grant(
        self,
        approved: CapabilitySet,
        requested: CapabilitySet,
        manifest_digest: str,
        pinned_digest: str,
    ) -> CapabilitySet: ...

    # INV-10 — memory is tenant-scoped and informational.
    def recall_memory(self, tenant: str) -> tuple[MemoryItem, ...]: ...

    # INV-12 — a shared limit is charged atomically (no check-then-act race).
    def budget_used_racing(self, limit: int, concurrent: int) -> int: ...

    # INV-14 — the harness ASSIGNS trust at an external boundary. Given the trust a tool
    # server *declares* for output crossing an external boundary, return the trust the
    # harness actually assigns; instruction-level claims must become untrusted data.
    def external_tool_trust(self, declared_trust: str) -> str: ...


@dataclass(frozen=True)
class ConformanceResult:
    invariant: str
    holds: bool
    detail: str = ""


@dataclass(frozen=True)
class ConformanceRun:
    adapter: str
    results: tuple[ConformanceResult, ...]

    @property
    def holds(self) -> dict[str, bool]:
        return {r.invariant: r.holds for r in self.results}

    @property
    def holding(self) -> int:
        return sum(1 for r in self.results if r.holds)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def broken(self) -> list[str]:
        return [r.invariant for r in self.results if not r.holds]

    @property
    def passed(self) -> bool:
        return self.holding == self.total
