import pytest

from dvah.guardrails.decision import Denied


@pytest.mark.adversarial
def test_revoked_action_denied_as_first_action(loaded):
    """Revoked action as the very first step — a first-decision cache still fails here."""
    with pytest.raises(Denied) as excinfo:
        loaded.harness.run_task(loaded.root_ctx, "DVAH-010-adversarial")
    assert excinfo.value.decision.invariant == "INV-09"
    assert loaded.files.exists("/prod/customer.db")
