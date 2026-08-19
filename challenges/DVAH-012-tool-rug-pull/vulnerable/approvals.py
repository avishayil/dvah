"""VULNERABLE approval service: binds without the tool digest (INV-11).

The binding key is computed over the operation only, omitting the tool/skill digest. So a
grant issued for one tool definition (digest D1) still validates the same operation after
the tool has been swapped for a different definition (digest D2) — a tool rug-pull.
"""

from __future__ import annotations

import itertools

from dvah.models.approval import ApprovalGrant
from dvah.models.hashing import sha256_of


def _predigest_key(env) -> str:
    # BUG: everything EXCEPT the tool/skill digest — survives a rug-pull.
    return sha256_of(
        {
            "actor": env.actor.model_dump(),
            "namespace": env.operation.namespace,
            "action": env.operation.action,
            "resource": env.operation.resource,
            "parameters_hash": env.operation.parameters_hash,
            "delegation": env.delegation.model_dump(),
            "tenant": env.principal.tenant,
        }
    )


class PreDigestApprovalService:
    def __init__(self) -> None:
        self._ids = itertools.count(1)

    def request(self, envelope) -> ApprovalGrant:
        return ApprovalGrant(
            approval_id=f"approval-{next(self._ids)}",
            approved_action_hash=_predigest_key(envelope),
        )

    def validate(self, envelope, grant) -> bool:
        return grant.approved_action_hash == _predigest_key(envelope)

    def find(self, grants, envelope):
        for grant in grants:
            if grant.approved_action_hash == _predigest_key(envelope):
                return grant
        return None
