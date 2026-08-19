"""Agent Harness Security Conformance suite.

The mutation probes proved DVAH's *own* harness holds the invariants. This package
lifts the same checks behind a runtime-agnostic ``HarnessAdapter`` so the invariant
battery (INV-01…12) can grade *any* agent runtime — DVAH's builtin harness, or an
external one (LangGraph, CrewAI, an MCP server) via a small adapter.

`dvah mutate` remains the adversarial sibling: it runs the equivalent battery against a
deliberately-broken builtin harness. This package runs it against a real adapter.
"""

from .adapter import (
    AdapterDecision,
    CompiledView,
    ConformanceResult,
    ConformanceRun,
    HarnessAdapter,
    MemoryItem,
    RunOutcome,
)
from .battery import INVARIANTS, run_battery
from .builtin_adapter import BuiltinAdapter
from .external_adapter import ExternalHarness

__all__ = [
    "AdapterDecision",
    "CompiledView",
    "ConformanceResult",
    "ConformanceRun",
    "HarnessAdapter",
    "MemoryItem",
    "RunOutcome",
    "INVARIANTS",
    "run_battery",
    "BuiltinAdapter",
    "ExternalHarness",
]
