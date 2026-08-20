"""FIXED budget tracker: one shared global budget across the delegation tree (INV-06)."""

from __future__ import annotations

from dvah.guardrails.budget import BuiltinBudgetTracker


class SharedBudgetTracker(BuiltinBudgetTracker):
    def __init__(self, limit: int = 3) -> None:
        super().__init__(limit=limit)
