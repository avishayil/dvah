"""Plan-step resolution: turn a proposed PlanStep into a concrete, authorizable action.

Resolution binds parameters NOW (execution time). The resulting ActionEnvelope is the
only thing that carries authority — the plan step does not.
"""

from __future__ import annotations

from ..models.envelope import ActionEnvelope
from ..models.operation import Operation
from ..providers.model import PlanStep
from .context import RunContext


def resolve_operation(step: PlanStep) -> Operation:
    return Operation(
        namespace=step.namespace,
        action=step.action,
        resource=step.resource,
        parameters=dict(step.parameters),
    )


def build_envelope(ctx: RunContext, operation: Operation) -> ActionEnvelope:
    return ActionEnvelope(
        action_id=ctx.next_action_id(),
        principal=ctx.principal,
        actor=ctx.actor,
        delegation=ctx.delegation,
        intent=ctx.intent,
        operation=operation,
        capabilities=ctx.capabilities,
        provenance=ctx.provenance,
        runtime=ctx.runtime,
        constraints=ctx.constraints,
    )
