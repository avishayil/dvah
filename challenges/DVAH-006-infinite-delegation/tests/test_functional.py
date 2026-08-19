import pytest


@pytest.mark.functional
def test_within_budget_task_succeeds(loaded):
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-006-functional")
    assert all(r.ok for r in results)
    assert len(results) == 2
