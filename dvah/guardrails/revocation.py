"""Revocation registry & authority leases (INV-09).

Authorization is not point-in-time: authority must be re-validated for the lifetime of a
running action, and a revocation issued mid-run must take effect on the next action.
The registry is consulted per resolved action (see ``BuiltinPolicy``); an empty registry
is a no-op, so existing labs are unaffected.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.envelope import ActionEnvelope


@dataclass(frozen=True)
class AuthorityLease:
    """A time-boxed grant. Uses injected ISO timestamps (never wall-clock)."""

    issued: str
    expires: str | None = None

    def valid_at(self, now: str) -> bool:
        # ISO-8601 strings compare lexicographically for the fixed harness format.
        return self.expires is None or now < self.expires


class RevocationRegistry:
    """A live set of revoked ``(namespace, action)`` operations and/or principals."""

    def __init__(
        self,
        revoked_actions: set[tuple[str, str]] | None = None,
        revoked_principals: set[str] | None = None,
    ) -> None:
        self._actions: set[tuple[str, str]] = set(revoked_actions or ())
        self._principals: set[str] = set(revoked_principals or ())

    def revoke_action(self, namespace: str, action: str) -> None:
        self._actions.add((namespace, action))

    def revoke_principal(self, user: str) -> None:
        self._principals.add(user)

    def is_revoked(self, envelope: ActionEnvelope) -> bool:
        op = envelope.operation
        return (
            (op.namespace, op.action) in self._actions
            or envelope.principal.user in self._principals
        )
