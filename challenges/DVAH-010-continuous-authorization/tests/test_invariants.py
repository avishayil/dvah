import pytest

from dvah.harness.resolver import build_envelope, resolve_operation
from dvah.providers.model import PlanStep
from dvah.security.decision import Verdict


def _authorize(policy, ctx, namespace, action, resource):
    env = build_envelope(
        ctx, resolve_operation(PlanStep(namespace=namespace, action=action, resource=resource))
    )
    return policy.authorize(env)


@pytest.mark.invariant("INV-09")
def test_revoked_action_denied_after_any_allows(loaded):
    """INV-09: a revoked action is denied regardless of how many actions were allowed first."""
    policy = loaded.harness.cfg.policy
    ctx = loaded.root_ctx
    for _ in range(3):  # prior allowed actions must not confer lasting authority
        _authorize(policy, ctx, "files", "read", "/tmp/scratch")
    decision = _authorize(policy, ctx, "files", "delete", "/prod/customer.db")
    assert decision.verdict is Verdict.DENY
    assert decision.invariant == "INV-09"
