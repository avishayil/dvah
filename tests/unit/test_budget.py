import pytest

from dvah.guardrails.budget import BuiltinBudgetTracker
from dvah.guardrails.decision import Denied


@pytest.mark.unit
@pytest.mark.parametrize("limit", [1, 3, 5])
def test_builtin_budget_allows_exactly_limit_then_denies(limit):
    tracker = BuiltinBudgetTracker(limit=limit)
    for _ in range(limit):
        tracker.charge(ctx=None)  # ctx is ignored by the shared tracker
    assert tracker.remaining() == 0
    with pytest.raises(Denied) as excinfo:
        tracker.charge(ctx=None)
    assert excinfo.value.decision.invariant == "INV-06"


@pytest.mark.unit
def test_remaining_decrements():
    tracker = BuiltinBudgetTracker(limit=2)
    assert tracker.remaining() == 2
    tracker.charge(ctx=None)
    assert tracker.remaining() == 1
