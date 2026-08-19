import pytest


@pytest.mark.functional
def test_permitted_operation_works(loaded):
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-008-functional")
    assert results[0].ok
    assert results[0].output["issues"][0]["id"] == 418
