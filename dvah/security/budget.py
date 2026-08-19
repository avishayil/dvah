"""Budget tracker (INV-06 budget arm).

The correct tracker enforces ONE shared action budget across the whole delegation
tree. A vulnerable tracker that keys on a per-agent counter lets every delegation mint
a fresh budget, so an unbounded number of actions runs by fanning out subagents.
"""

from __future__ import annotations

import threading
from typing import Protocol, runtime_checkable

from .decision import Decision, Denied, Verdict


@runtime_checkable
class BudgetTracker(Protocol):
    def charge(self, ctx: "RunContext") -> None: ...  # noqa: F821
    def remaining(self) -> int: ...


class BuiltinBudgetTracker:
    """Shared, monotonically-decrementing global action budget.

    The check-then-increment is guarded by a lock so it is **atomic** (INV-12): two
    concurrent charges can never both observe ``used < limit`` and slip past a shared
    limit. A non-atomic version (see ``mutation.broken.RacyBudgetTracker``) is the
    intended defeat.
    """

    def __init__(self, limit: int = 1000) -> None:
        self._limit = limit
        self._used = 0
        self._lock = threading.Lock()

    def charge(self, ctx: "RunContext") -> None:  # noqa: F821
        with self._lock:
            if self._used >= self._limit:
                raise Denied(
                    Decision(
                        verdict=Verdict.DENY,
                        reason="action budget exhausted",
                        invariant="INV-06",
                    )
                )
            self._used += 1

    def remaining(self) -> int:
        return max(0, self._limit - self._used)
