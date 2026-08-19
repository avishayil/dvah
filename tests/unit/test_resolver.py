import pytest

from dvah.harness.resolver import build_envelope, resolve_operation
from dvah.providers.model import PlanStep

pytestmark = pytest.mark.unit


def test_resolve_operation_maps_fields():
    step = PlanStep(namespace="files", action="delete", resource="/x", parameters={"k": "v"})
    op = resolve_operation(step)
    assert (op.namespace, op.action, op.resource) == ("files", "delete", "/x")
    assert op.parameters == {"k": "v"}


def test_build_envelope_copies_context_fields(make_ctx):
    ctx = make_ctx(agent_id="a1", task_id="task-9")
    op = resolve_operation(PlanStep(namespace="files", action="read", resource="/x"))
    env = build_envelope(ctx, op)
    assert env.action_id == ctx.next_action_id()
    assert env.actor.agent_id == "a1"
    assert env.intent.task_id == "task-9"
    assert env.operation is op
    assert env.capabilities is ctx.capabilities
