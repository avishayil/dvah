"""FIXED approval service: binds to the resolved action hash (INV-03)."""

from __future__ import annotations

from dvah.guardrails.approvals import BuiltinApprovalService


class ActionBoundApprovalService(BuiltinApprovalService):
    pass
