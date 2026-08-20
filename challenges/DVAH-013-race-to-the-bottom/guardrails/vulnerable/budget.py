"""VULNERABLE budget tracker: non-atomic check-then-act (INV-12).

``steps`` exposes the charge as two separate scheduler operations — a check and a commit.
Interleaved across two agents, both checks observe room before either commits, so both
commit and an extra action slips past the limit.
"""

from __future__ import annotations

from dvah.guardrails.decision import Decision, Denied, Verdict


class RacyBudgetTracker:
    def __init__(self, limit: int = 1) -> None:
        self._limit = limit
        self._used = 0

    def charge(self, ctx) -> None:
        # Single-agent (non-interleaved) path — safe only because nothing runs between
        # the check and the increment here.
        if self._used >= self._limit:
            raise Denied(Decision(verdict=Verdict.DENY, reason="budget exhausted", invariant="INV-12"))
        self._used += 1

    def remaining(self) -> int:
        return max(0, self._limit - self._used)

    def steps(self, ctx, out: list):
        """Return the charge as TWO scheduler ops — the check-then-act gap is the bug."""
        state: dict = {}

        def check() -> None:
            state["allowed"] = self._used < self._limit  # BUG: decided before committing

        def commit() -> None:
            if state.get("allowed"):
                self._used += 1
                out.append("ok")
            else:
                out.append("denied")

        return [check, commit]
