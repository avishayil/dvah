import pytest

from dvah.models.operation import Operation
from dvah.security.approvals import BuiltinApprovalService

pytestmark = pytest.mark.unit


def test_request_binds_to_action_hash(make_envelope):
    env = make_envelope()
    grant = BuiltinApprovalService().request(env)
    assert grant.approved_action_hash == env.action_hash


def test_validate_true_for_same_envelope(make_envelope):
    env = make_envelope()
    svc = BuiltinApprovalService()
    assert svc.validate(env, svc.request(env))


def test_validate_false_for_mutated_operation(make_envelope):
    env = make_envelope(operation=Operation(namespace="email", action="send", resource="m",
                                            parameters={"to": "bob"}))
    svc = BuiltinApprovalService()
    grant = svc.request(env)
    mutated = env.with_operation(env.operation.with_parameters({"to": "all-customers"}))
    assert not svc.validate(mutated, grant)


def test_approval_ids_are_unique(make_envelope):
    svc = BuiltinApprovalService()
    env = make_envelope()
    assert svc.request(env).approval_id != svc.request(env).approval_id


def test_request_records_approver(make_envelope):
    svc = BuiltinApprovalService(approver="alice")
    grant = svc.request(make_envelope())
    assert grant.approver == "alice"


def test_one_time_grant_cannot_be_replayed(make_envelope):
    """Review #2: a one-time approval authorizes exactly one execution."""
    env = make_envelope()
    svc = BuiltinApprovalService()
    grant = svc.request(env, one_time=True)
    assert svc.validate(env, grant) is True   # first use ok
    svc.consume(grant)                          # broker consumes after execution
    assert svc.validate(env, grant) is False   # replay denied


def test_reusable_grant_is_not_consumed(make_envelope):
    env = make_envelope()
    svc = BuiltinApprovalService()
    grant = svc.request(env)                    # default: reusable
    svc.consume(grant)                          # no-op for non-one_time
    assert svc.validate(env, grant) is True


def test_expired_grant_is_rejected(make_envelope):
    env = make_envelope()
    svc = BuiltinApprovalService(clock="2026-01-02T00:00:00Z")
    grant = svc.request(env, expires="2026-01-01T00:00:00Z")
    assert svc.validate(env, grant) is False
