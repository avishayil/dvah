"""FIXED budget tracker: atomic check-and-commit (INV-12).

``steps`` exposes the whole charge as ONE indivisible scheduler op, so no interleaving
can place another agent's action between the check and the increment.
"""

from __future__ import annotations

import threading

from dvah.security.decision import Decision, Denied, Verdict


class AtomicBudgetTracker:
    def __init__(self, limit: int = 1) -> None:
        self._limit = limit
        self._used = 0
        self._lock = threading.Lock()

    def charge(self, ctx) -> None:
        with self._lock:  # check + increment in one critical section
            if self._used >= self._limit:
                raise Denied(Decision(verdict=Verdict.DENY, reason="budget exhausted", invariant="INV-12"))
            self._used += 1

    def remaining(self) -> int:
        with self._lock:
            return max(0, self._limit - self._used)

    def steps(self, ctx, out: list):
        """The atomic charge is a single, indivisible scheduler op."""

        def charge_once() -> None:
            try:
                self.charge(ctx)
                out.append("ok")
            except Denied:
                out.append("denied")

        return [charge_once]
