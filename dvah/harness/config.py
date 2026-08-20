"""HarnessConfig — the dependency-injection container.

Challenges construct a config with one or more slots replaced by deliberately-broken
implementations. Everything the broker needs is reachable from here, so a lab can
break exactly one component and leave the rest correct.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ..models.runtime import Constraints
from ..observability.trace import TraceLog
from ..providers.model import ModelProvider
from ..providers.tools import ToolProvider
from ..guardrails.approvals import ApprovalService
from ..guardrails.capabilities import CapabilityResolver
from ..guardrails.policy import PolicyEngine
from ..guardrails.budget import BudgetTracker, BuiltinBudgetTracker
from ..guardrails.provenance import ProvenanceTracker
from ..guardrails.secrets import SecretBroker
from ..guardrails.revocation import RevocationRegistry
from ..guardrails.skills import BuiltinSkillLoader, SkillLoader
from ..memory.store import BuiltinMemoryProvider, MemoryProvider
from .compiler import BuiltinContextCompiler, ContextCompiler
from .executor import Executor
from .scheduler import Scheduler, SequentialScheduler


@dataclass(frozen=True)
class HarnessConfig:
    model: ModelProvider
    policy: PolicyEngine
    approvals: ApprovalService
    capabilities: CapabilityResolver
    provenance: ProvenanceTracker
    secrets: SecretBroker
    tools: ToolProvider
    executor: Executor
    trace: TraceLog
    constraints: Constraints = field(default_factory=Constraints)
    #: Fixed timestamp injected into provenance so runs stay deterministic.
    clock: str = "2026-01-01T00:00:00Z"
    context_compiler: ContextCompiler = field(default_factory=BuiltinContextCompiler)
    budget: BudgetTracker = field(default_factory=BuiltinBudgetTracker)
    # Phase-1 slots (defaulted → existing labs/configs unaffected; labs override them).
    skill_loader: SkillLoader = field(default_factory=BuiltinSkillLoader)
    revocation: RevocationRegistry = field(default_factory=RevocationRegistry)
    memory: MemoryProvider = field(default_factory=BuiltinMemoryProvider)
    scheduler: Scheduler = field(default_factory=SequentialScheduler)

    def with_slots(self, **overrides: Any) -> "HarnessConfig":
        return replace(self, **overrides)
