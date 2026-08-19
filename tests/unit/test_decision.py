import pytest

from dvah.security.decision import Decision, Denied, Verdict

pytestmark = pytest.mark.unit


def test_denied_carries_decision_and_formats_message():
    decision = Decision(verdict=Verdict.DENY, reason="nope", invariant="INV-01")
    err = Denied(decision)
    assert err.decision is decision
    assert str(err) == "INV-01: nope"


def test_denied_without_invariant_uses_deny_label():
    err = Denied(Decision(verdict=Verdict.DENY, reason="nope"))
    assert str(err) == "DENY: nope"
