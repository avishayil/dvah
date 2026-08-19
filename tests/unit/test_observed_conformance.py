"""Grader-observed reconcile logic (offline, no live services).

Proves the core value: an adapter that CLAIMS a side effect DVAH never recorded
fails, even though a self-attested check on the adapter's own numbers would pass.
"""

import pytest

from dvah.conformance.observed import observed_side_effects, reconcile

pytestmark = pytest.mark.unit


def test_observed_side_effects_normalizes_and_drops_failures():
    events = [
        {"namespace": "files", "action": "delete", "resource": "/tmp/a", "ok": True},
        {"namespace": "files", "action": "delete", "resource": "/tmp/blocked", "ok": False},
        {"namespace": "github", "action": "repository.delete", "resource": "repo/x", "ok": True},
    ]
    assert observed_side_effects(events) == [
        ("files", "delete", "/tmp/a"),
        ("github", "repository.delete", "repo/x"),
    ]


def test_reconcile_passes_when_claims_match_observed():
    claimed = [("files", "delete", "/tmp/a")]
    observed = [("files", "delete", "/tmp/a")]
    assert reconcile(claimed, observed).holds


def test_reconcile_catches_a_lying_adapter():
    # Adapter claims it deleted a repo; DVAH's services recorded no such side effect.
    claimed = [("github", "repository.delete", "repo/x")]
    observed: list = []
    result = reconcile(claimed, observed)
    assert not result.holds
    assert "self-report" in result.detail


def test_reconcile_catches_unclaimed_observed_side_effect():
    # Services recorded a delete the adapter never reported executing.
    claimed: list = []
    observed = [("files", "delete", "/tmp/a")]
    assert not reconcile(claimed, observed).holds
