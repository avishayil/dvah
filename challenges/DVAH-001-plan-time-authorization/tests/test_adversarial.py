import pytest

from dvah.security.decision import Denied


@pytest.mark.adversarial
def test_a_different_unauthorized_action_is_also_blocked(loaded):
    """A patch that only guards deletes must not let an unauthorized rename through."""
    with pytest.raises(Denied) as excinfo:
        loaded.harness.run_task(loaded.root_ctx, "DVAH-001-adversarial")
    assert excinfo.value.decision.invariant == "INV-01"
    assert loaded.files.exists("/prod/customer.db")
