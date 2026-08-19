"""Approval grant — APPROVED BY WHOM dimension.

A grant binds a human decision to a specific resolved action via its ``action_hash``.
Binding to the hash (not a plan id) is INV-03: replanning cannot reuse an old approval.

A grant also records *who* approved and *when*, may expire, and may be ``one_time`` —
authorizing exactly one execution. One-time grants are consumed by the broker after a
successful execution so a replay of the same resolved action cannot recycle them
(reusable grants keep the historical behavior).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApprovalGrant(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_id: str
    approved_action_hash: str
    approver: str = ""            # identity of the human/principal who approved
    issued: str = ""             # ISO timestamp the grant was issued
    expires: str | None = None    # ISO timestamp after which the grant is invalid
    one_time: bool = False        # if True, authorizes exactly one execution
