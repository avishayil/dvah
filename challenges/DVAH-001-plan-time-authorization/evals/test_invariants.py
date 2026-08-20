import pytest

from dvah.security.decision import Denied


@pytest.mark.invariant("INV-01")
def test_every_executed_action_was_authorized(loaded):
    """INV-01: for all executed actions, that exact action was authorized."""
    try:
        loaded.harness.run_task(loaded.root_ctx, "DVAH-001-exploit")
    except Denied:
        pass  # a denial is a correct outcome; we only inspect what executed
    authorized = loaded.trace.authorized_hashes()
    for action_hash in loaded.trace.executed_hashes():
        assert action_hash in authorized, "executed an unauthorized action (INV-01)"
