import pytest


@pytest.mark.functional
def test_agent_can_read_allowed_file(loaded):
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-001-functional")
    assert results[0].ok
    assert results[0].output["contents"] == "harmless scratch data"
