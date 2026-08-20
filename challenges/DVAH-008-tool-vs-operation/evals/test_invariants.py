import pytest

from dvah.harness.resolver import build_envelope
from dvah.models.operation import Operation
from dvah.security.decision import Verdict


@pytest.mark.invariant("INV-13")
def test_capability_for_one_action_does_not_cover_another(loaded):
    """INV-13 / tool-vs-operation: holding issue.read must not authorize other ops."""
    for action in ["repository.delete", "secret.create", "workflow.modify"]:
        op = Operation(namespace="github", action=action, resource="repo/acme/payments")
        env = build_envelope(loaded.root_ctx, op)
        decision = loaded.harness.cfg.policy.authorize(env)
        assert decision.verdict is Verdict.DENY, f"{action} should not be permitted"
