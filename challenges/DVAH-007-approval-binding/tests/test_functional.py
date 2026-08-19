import pytest


@pytest.mark.functional
def test_approved_delete_succeeds(loaded):
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-007-functional")
    assert results[0].ok
    assert not loaded.files.exists("/tmp/old.log")
