"""FIXED executor: authorize each resolved action immediately before execution.

Every step is routed through the broker's gate (INV-01). Delegation steps go through
the agent runtime, exactly like the built-in correct executor.
"""

from __future__ import annotations

_DELEGATE = ("agent", "delegate")


class PerActionExecutor:
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
