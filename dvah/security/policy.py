"""Policy engine — the authorization brain (INV-08 attribution, INV-13 operation-granular).

The correct default authorizes the *resolved* operation against the capabilities
carried on the envelope, keyed on (principal, actor, operation, resource, params),
never on a bare tool name (INV-13). It also requires a complete attribution chain (INV-08).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.envelope import ActionEnvelope
from .decision import Decision, Verdict


@runtime_checkable
class PolicyEngine(Protocol):
    def authorize(self, envelope: ActionEnvelope) -> Decision: ...


#: Operations that require an explicit human approval even when capabilities permit.
DEFAULT_APPROVAL_ACTIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("files", "delete"),
        ("github", "repository.delete"),
        ("cloud", "instance.terminate"),
        ("email", "send"),
    }
)


class BuiltinPolicy:
    """Correct reference policy. Authorizes on the resolved operation.

    Optionally consults a live revocation registry so authority is re-validated on every
    resolved action (INV-09) — a revocation issued mid-run denies the next action. With
    no registry (the default) behavior is unchanged.
    """

    def __init__(
        self,
        approval_actions: frozenset[tuple[str, str]] = DEFAULT_APPROVAL_ACTIONS,
        revocation=None,
    ) -> None:
        self._approval_actions = approval_actions
        self._revocation = revocation

    def authorize(self, envelope: ActionEnvelope) -> Decision:
        op = envelope.operation

        # INV-08: every action must be fully attributable, and the attribution chain
        # must actually *correspond* to the principal and acting agent — not merely be
        # non-empty. A forged envelope (root_principal != principal, or a chain tip that
        # isn't the actor) is denied even though each field is individually present.
        deleg = envelope.delegation
        if (
            not deleg.root_principal
            or not deleg.chain
            or not envelope.actor.agent_id
            or deleg.root_principal != envelope.principal.user
            or deleg.chain[-1] != envelope.actor.agent_id
        ):
            return Decision(
                verdict=Verdict.DENY,
                reason="action lacks a complete, self-consistent attribution chain",
                invariant="INV-08",
            )

        # INV-09: authority is re-validated per action against live revocations.
        if self._revocation is not None and self._revocation.is_revoked(envelope):
            return Decision(
                verdict=Verdict.DENY,
                reason=f"authority for {op.namespace}.{op.action} was revoked",
                invariant="INV-09",
            )

        # INV-01 complete mediation, enforced at operation granularity (upholds INV-13):
        # authorize the specific resolved operation, never the bare tool namespace.
        if not envelope.capabilities.permits(op.namespace, op.action):
            return Decision(
                verdict=Verdict.DENY,
                reason=f"no capability for {op.namespace}.{op.action}",
                invariant="INV-01",
            )

        if (op.namespace, op.action) in self._approval_actions:
            return Decision(
                verdict=Verdict.NEEDS_APPROVAL,
                reason=f"{op.namespace}.{op.action} requires human approval",
            )

        return Decision(verdict=Verdict.ALLOW, reason="capability permits operation")
