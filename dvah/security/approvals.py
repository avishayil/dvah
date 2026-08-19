"""Approval service — binds human consent to a specific resolved action (INV-03).

The correct default issues a grant carrying the envelope's ``action_hash`` and
validates by comparing hashes. A grant for one action therefore cannot authorize a
different resolved action produced by replanning.
"""

from __future__ import annotations

import itertools
from typing import Protocol, runtime_checkable

from ..models.approval import ApprovalGrant
from ..models.envelope import ActionEnvelope


@runtime_checkable
class ApprovalService(Protocol):
    def request(self, envelope: ActionEnvelope) -> ApprovalGrant: ...
    def validate(self, envelope: ActionEnvelope, grant: ApprovalGrant) -> bool: ...
    def find(
        self, grants: tuple[ApprovalGrant, ...], envelope: ActionEnvelope
    ) -> ApprovalGrant | None: ...


class BuiltinApprovalService:
    """Correct reference approval service; auto-approves in this simulated env.

    A carried grant is reused only when it binds to the *exact* resolved action
    (INV-03) — replanning that changes the action cannot recycle an old approval.
    Grants record the approver, may expire, and may be ``one_time`` (consumed after a
    single execution so replays can't recycle them).
    """

    def __init__(self, approver: str = "operator", clock: str | None = None) -> None:
        self._ids = itertools.count(1)
        self._approver = approver
        self._clock = clock or ""
        self._consumed: set[str] = set()

    def request(self, envelope: ActionEnvelope, *, one_time: bool = False,
                expires: str | None = None) -> ApprovalGrant:
        return ApprovalGrant(
            approval_id=f"approval-{next(self._ids)}",
            approved_action_hash=envelope.action_hash,
            approver=self._approver,
            issued=self._clock,
            expires=expires,
            one_time=one_time,
        )

    def validate(self, envelope: ActionEnvelope, grant: ApprovalGrant) -> bool:
        if grant.approved_action_hash != envelope.action_hash:
            return False
        if grant.expires is not None and self._clock and self._clock >= grant.expires:
            return False  # grant has expired
        if grant.one_time and grant.approval_id in self._consumed:
            return False  # one-time grant already spent — no replay
        return True

    def consume(self, grant: ApprovalGrant) -> None:
        """Mark a one-time grant as spent (called by the broker after execution)."""
        if grant.one_time:
            self._consumed.add(grant.approval_id)

    def find(
        self, grants: tuple[ApprovalGrant, ...], envelope: ActionEnvelope
    ) -> ApprovalGrant | None:
        for grant in grants:
            if grant.approved_action_hash == envelope.action_hash:
                return grant
        return None
