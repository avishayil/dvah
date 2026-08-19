import pytest

from dvah.mutation.engine import run
from dvah.mutation.flags import ALL_FLAGS, FLAG_TO_INV, MutationFlags


@pytest.mark.integration
def test_no_defeats_all_invariants_hold():
    result = run(MutationFlags())
    assert result.holding == result.total
    assert result.broken == []


@pytest.mark.integration
@pytest.mark.parametrize("flag", ALL_FLAGS)
def test_single_defeat_breaks_only_its_invariant(flag):
    result = run(MutationFlags(**{flag: True}))
    assert result.broken == [FLAG_TO_INV[flag]], f"{flag} should isolate to one invariant"


@pytest.mark.integration
def test_multiple_defeats_break_the_expected_set():
    result = run(MutationFlags(execution_authz=True, tool_vs_operation=True))
    assert set(result.broken) == {"INV-01", "INV-13"}
    assert result.holding == result.total - 2
