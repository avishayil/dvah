import pytest
from pydantic import ValidationError

from dvah.models.approval import ApprovalGrant
from dvah.models.operation import Operation

pytestmark = pytest.mark.unit


def test_action_hash_stable_across_action_id_changes(make_ctx, make_envelope):
    ctx = make_ctx()
    env1 = make_envelope(ctx=ctx)
    env2 = make_envelope(ctx=ctx.tick())  # different action_id
    assert env1.action_id != env2.action_id
    assert env1.action_hash == env2.action_hash


def test_action_hash_changes_with_resource(make_envelope):
    a = make_envelope(operation=Operation(namespace="files", action="read", resource="/a"))
    b = make_envelope(operation=Operation(namespace="files", action="read", resource="/b"))
    assert a.action_hash != b.action_hash


def test_action_hash_changes_with_parameters(make_envelope):
    a = make_envelope(operation=Operation(namespace="e", action="send", resource="m", parameters={"to": "x"}))
    b = make_envelope(operation=Operation(namespace="e", action="send", resource="m", parameters={"to": "y"}))
    assert a.action_hash != b.action_hash


def test_action_hash_changes_with_delegation(make_ctx, make_envelope):
    base = make_envelope(ctx=make_ctx(agent_id="root"))
    child_ctx = make_ctx(agent_id="root")
    child_ctx = child_ctx.child("child", "child-inst", child_ctx.capabilities)
    delegated = make_envelope(ctx=child_ctx)
    assert base.action_hash != delegated.action_hash


def test_with_approval_returns_new_copy(make_envelope):
    env = make_envelope()
    grant = ApprovalGrant(approval_id="a1", approved_action_hash=env.action_hash)
    env2 = env.with_approval(grant)
    assert env2.approval == grant
    assert env.approval is None


def test_with_operation_returns_new_copy(make_envelope):
    env = make_envelope()
    env2 = env.with_operation(Operation(namespace="files", action="delete", resource="/z"))
    assert env2.operation.action == "delete"
    assert env.operation.action == "read"


def test_envelope_is_frozen(make_envelope):
    env = make_envelope()
    with pytest.raises(ValidationError):
        env.action_id = "x"
