import pytest

from dvah.security.decision import Denied


@pytest.mark.adversarial
def test_budget_is_a_shared_global_cap(loaded):
    """The budget must exhaust across repeated charges, not reset per agent."""
    budget = loaded.harness.cfg.budget
    ctx = loaded.root_ctx  # actions_used stays 0 — a per-agent tracker would never trip
    charged = 0
    with pytest.raises(Denied) as excinfo:
        for _ in range(100):
            budget.charge(ctx)
            charged += 1
    assert excinfo.value.decision.invariant == "INV-06"
    assert charged < 100
