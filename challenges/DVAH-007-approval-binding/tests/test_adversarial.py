import pytest

from dvah.harness.resolver import build_envelope
from dvah.models.operation import Operation


@pytest.mark.adversarial
@pytest.mark.parametrize("resource", ["/prod/customer.db", "/tmp/other", "/etc/shadow"])
def test_grant_never_validates_a_different_resolved_action(loaded, resource):
    """An approval for one delete must not authorize a delete of anything else."""
    ctx = loaded.root_ctx
    approved = build_envelope(ctx, Operation(namespace="files", action="delete", resource="/tmp/approved"))
    grant = loaded.harness.cfg.approvals.request(approved)
    other = build_envelope(ctx, Operation(namespace="files", action="delete", resource=resource))
    assert not loaded.harness.cfg.approvals.validate(other, grant)
    assert loaded.harness.cfg.approvals.validate(approved, grant)
