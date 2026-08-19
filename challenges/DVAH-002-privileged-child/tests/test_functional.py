import pytest


@pytest.mark.functional
def test_delegated_child_can_read_within_scope(loaded):
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-002-functional")
    assert results[0].ok
    assert results[0].output["issues"][0]["id"] == 418
