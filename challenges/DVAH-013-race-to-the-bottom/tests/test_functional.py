import pytest


@pytest.mark.functional
def test_single_charge_within_limit_succeeds(loaded):
    """A lone charge within the limit succeeds for both the racy and atomic tracker."""
    Tracker = type(loaded.harness.cfg.budget)
    tracker = Tracker()
    out: list = []
    for op in tracker.steps(loaded.root_ctx, out):
        op()
    assert out.count("ok") == 1
