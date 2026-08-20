"""INV-12: the shared budget must be charged atomically (review #6).

The old conformance "race" was a sequential loop, so a non-atomic check-then-act
tracker passed. These tests (a) prove the atomic BuiltinBudgetTracker holds the shared
limit under real threaded contention, and (b) prove the same invariant assertion CATCHES
a non-atomic tracker, using the deterministic check/commit interleaving from
mutation.broken.RacyBudgetTracker (no flaky threads needed for the failing case).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from dvah.conformance.builtin_adapter import BuiltinAdapter
from dvah.mutation.broken import RacyBudgetTracker
from dvah.guardrails.budget import BuiltinBudgetTracker
from dvah.guardrails.decision import Denied


@pytest.mark.unit
def test_atomic_tracker_never_exceeds_limit_under_contention() -> None:
    """Many threads racing a shared limit charge at most `limit` times — always."""
    for _ in range(50):  # repeat: the lock makes the pass deterministic, not lucky
        limit = 5
        tracker = BuiltinBudgetTracker(limit=limit)
        barrier = threading.Barrier(32)
        succeeded = 0
        lock = threading.Lock()

        def attempt() -> None:
            nonlocal succeeded
            barrier.wait()
            try:
                tracker.charge(None)
            except Denied:
                return
            with lock:
                succeeded += 1

        with ThreadPoolExecutor(max_workers=32) as pool:
            for f in [pool.submit(attempt) for _ in range(32)]:
                f.result()

        assert succeeded == limit
        assert tracker.remaining() == 0


@pytest.mark.unit
def test_conformance_probe_races_for_real() -> None:
    """The adapter's budget_used_racing uses real threads and respects the atomic limit."""
    used = BuiltinAdapter().budget_used_racing(limit=1, concurrent=8)
    assert used <= 1


@pytest.mark.unit
def test_invariant_assertion_catches_non_atomic_tracker() -> None:
    """A non-atomic check-then-act tracker over-charges under interleaving — and the
    INV-12 assertion (`used <= limit`) flags it. Deterministic: two chargers both pass
    check() before either commits, so both slip past a limit of 1."""
    racy = RacyBudgetTracker(limit=1)
    # Interleave: both observe headroom, then both commit — the check-then-act gap.
    assert racy.check() and racy.check()
    racy.commit()
    racy.commit()
    used = racy.used
    assert used == 2
    # This is exactly what the conformance probe asserts against; a non-atomic tracker fails it.
    assert not (used <= racy.limit)
