"""Unit tests for the conformance battery + adapters."""

from __future__ import annotations

import pytest

from dvah.conformance import (
    BuiltinAdapter,
    ExternalHarness,
    HarnessAdapter,
    run_battery,
)
from dvah.conformance.battery import INVARIANTS

pytestmark = pytest.mark.unit


def test_adapters_satisfy_protocol():
    assert isinstance(BuiltinAdapter(), HarnessAdapter)
    assert isinstance(ExternalHarness(), HarnessAdapter)


def test_builtin_adapter_holds_all_invariants():
    run = run_battery(BuiltinAdapter())
    assert run.passed, f"builtin should hold all invariants; broke: {run.broken}"
    assert run.holding == run.total == len(INVARIANTS)


def test_battery_covers_the_invariants():
    run = run_battery(BuiltinAdapter())
    assert set(run.holds.keys()) == set(INVARIANTS)
    # INV-01..14 with INV-06 split into instruction/data + budget → 15 probe keys.
    assert len(INVARIANTS) == 15


def test_external_mock_fails_exactly_its_two_defects():
    run = run_battery(ExternalHarness())
    assert set(run.broken) == {"INV-01", "INV-11"}
    assert not run.passed
    # everything else on the foreign runtime conforms
    assert run.holding == run.total - 2
