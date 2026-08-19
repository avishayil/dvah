import pytest

from dvah.harness.resolver import build_envelope
from dvah.models.operation import Operation
from dvah.security.decision import Verdict


@pytest.mark.adversarial
@pytest.mark.parametrize(
    "action", ["repository.delete", "workflow.modify", "secret.create", "issue.comment"]
)
def test_other_operations_in_the_same_namespace_are_denied(loaded, action):
    """Holding issue.read must not authorize any other github operation."""
    ctx = loaded.root_ctx  # agent holds only github:issue.read
    env = build_envelope(ctx, Operation(namespace="github", action=action, resource="repo/acme/x"))
    assert loaded.harness.cfg.policy.authorize(env).verdict is Verdict.DENY
