import pytest

from dvah.guardrails.decision import Denied


class _FakeCtx:
    """A ctx whose per-agent counter never trips a per-agent check."""

    actions_used = 0

    class constraints:  # noqa: N801
        max_actions = 10_000_000


@pytest.mark.invariant("INV-06")
def test_configured_budget_is_globally_bounded(loaded):
    """INV-06: the configured budget must eventually stop, regardless of per-agent state."""
    tracker = loaded.harness.cfg.budget
    raised = False
    for _ in range(10_000):
        try:
            tracker.charge(_FakeCtx())
        except Denied:
            raised = True
            break
    assert raised, "budget is not globally bounded (INV-06)"
