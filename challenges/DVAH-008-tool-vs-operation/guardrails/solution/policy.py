"""FIXED policy: authorize the specific operation, not the tool name (INV-13)."""

from __future__ import annotations

from dvah.guardrails.policy import BuiltinPolicy


class FixedPolicy(BuiltinPolicy):
    pass
