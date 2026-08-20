"""VULNERABLE approval service: binds to the plan, not the resolved action (INV-03).

``request`` issues a grant keyed on a constant plan id; ``validate`` accepts any grant;
``find`` returns any existing grant. So one approval authorizes every later action.
"""

from __future__ import annotations

import itertools

from dvah.models.approval import ApprovalGrant

_PLAN_ID = "sha256:plan-DVAH-007"


class VulnerablePlanApprovalService:
    def __init__(self) -> None:
        self._ids = itertools.count(1)

    def request(self, envelope) -> ApprovalGrant:
        # BUG: bound to a constant plan id, not the resolved action.
        return ApprovalGrant(
            approval_id=f"approval-{next(self._ids)}", approved_action_hash=_PLAN_ID
        )

    def validate(self, envelope, grant) -> bool:
        return True  # BUG: accepts any grant for any action

    def find(self, grants, envelope):
        return grants[0] if grants else None  # BUG: reuses any prior approval
