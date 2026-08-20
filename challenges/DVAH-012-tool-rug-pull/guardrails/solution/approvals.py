"""FIXED approval service: binds to the full resolved action_hash (INV-11).

``action_hash`` includes the tool/skill digest, so a grant issued for one tool definition
cannot validate the same operation after the tool is swapped.
"""

from __future__ import annotations

from dvah.guardrails.approvals import BuiltinApprovalService


class FixedApprovalService(BuiltinApprovalService):
    pass
