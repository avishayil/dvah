"""VULNERABLE budget tracker: per-agent budget that resets on delegation (INV-06).

Because ``RunContext.actions_used`` resets for each child, every delegated subagent is
handed a fresh allowance and the global action count is unbounded.
"""

from __future__ import annotations

from dvah.security.decision import Decision, Denied, Verdict


class VulnerableBudgetTracker:
    def charge(self, ctx) -> None:
        # BUG: bounds each agent individually; delegation mints new budget.
        if ctx.actions_used >= ctx.constraints.max_actions:
            raise Denied(
                Decision(verdict=Verdict.DENY, reason="per-agent budget exhausted",
                         invariant="INV-06")
            )

    def remaining(self) -> int:
        return 0
