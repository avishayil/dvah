"""VULNERABLE executor: authorize once at plan time, then execute everything.

The bug (INV-01): the resolved delete action is never authorized at execution time,
so a capability the agent does not hold is exercised anyway. Note it still emits
``executed`` trace events, so the invariant test can see the unauthorized execution.
"""

from __future__ import annotations

from dvah.harness.resolver import build_envelope, resolve_operation
from dvah.guardrails.decision import Denied, Verdict


class VulnerableExecutor:
    def execute_plan(self, harness, ctx, steps):
        cfg = harness.cfg
        task_id = ctx.intent.task_id

        # BUG: authorize only the first step, once, at plan time.
        first_env = build_envelope(ctx, resolve_operation(steps[0]))
        decision = cfg.policy.authorize(first_env)
        cfg.trace.emit("policy.decision", task_id, first_env.action_hash,
                       action_id=first_env.action_id,
                       verdict=decision.verdict.value, invariant=decision.invariant,
                       reason="plan-time authorization (once)")
        if decision.verdict is Verdict.DENY:
            raise Denied(decision)

        results = []
        for step in steps:
            op = resolve_operation(step)
            env = build_envelope(ctx, op)
            credential = cfg.secrets.resolve(op.namespace, op)
            result = cfg.tools.invoke(op, credential)  # no per-action authorization
            cfg.trace.emit("executed", task_id, env.action_hash, action_id=env.action_id,
                           ok=result.ok,
                           namespace=op.namespace, action=op.action, resource=op.resource)
            results.append(result)
        return results
