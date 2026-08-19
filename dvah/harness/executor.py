"""Executor — drives a plan's steps. A swappable slot (DVAH-001 breaks it).

The correct executor routes every step through the broker's per-action gate (or the
agent for delegation). A vulnerable executor may authorize once and then execute many
actions, or call tools directly, bypassing the gate.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..providers.model import PlanStep
from ..providers.tools import ToolResult
from .context import RunContext

_DELEGATE = ("agent", "delegate")
_REFLECT = ("agent", "reflect")


@runtime_checkable
class Executor(Protocol):
    def execute_plan(
        self, harness: "Harness", ctx: RunContext, steps: tuple[PlanStep, ...]  # noqa: F821
    ) -> list[ToolResult]: ...


class BuiltinExecutor:
    """Correct executor: authorize-and-execute each resolved action in turn.

    ``agent.delegate`` spawns a subagent; ``agent.reflect`` compiles the accumulated
    context and lets the model propose follow-up actions from it.
    """

    def execute_plan(
        self, harness: "Harness", ctx: RunContext, steps: tuple[PlanStep, ...]  # noqa: F821
    ) -> list[ToolResult]:
        results: list[ToolResult] = []
        for step in steps:
            if (step.namespace, step.action) == _DELEGATE:
                results.extend(harness.delegate(ctx, step))
                continue
            if (step.namespace, step.action) == _REFLECT:
                results.extend(harness.reflect(ctx, step))
                continue
            outcome = harness.broker.run_step(ctx, step)
            ctx = outcome.ctx
            results.append(outcome.result)
        harness.last_ctx = ctx
        return results
