import pytest


@pytest.mark.functional
def test_allowed_read_runs(loaded):
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-010-functional")
    assert results[0].ok
