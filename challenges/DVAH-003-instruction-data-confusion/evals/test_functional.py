import pytest


@pytest.mark.functional
def test_agent_can_read_issue(loaded):
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-003-functional")
    assert results[0].ok
    assert results[0].output["issues"][0]["id"] == 418
