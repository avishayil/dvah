"""FIXED policy: re-validate every resolved action against live revocations (INV-09)."""

from __future__ import annotations

from dvah.guardrails.policy import BuiltinPolicy
from dvah.guardrails.revocation import RevocationRegistry


class RevokedActionPolicy:
    def __init__(self) -> None:
        # files:delete has been revoked; a running task must not still exercise it.
        registry = RevocationRegistry(revoked_actions={("files", "delete")})
        self._base = BuiltinPolicy(revocation=registry)

    def authorize(self, envelope):
        return self._base.authorize(envelope)
