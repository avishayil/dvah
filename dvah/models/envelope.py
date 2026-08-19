"""The ActionEnvelope — DVAH's central primitive.

Every side-effectful operation is resolved into exactly one frozen envelope
immediately before execution. Authorization, approval, capability checks, provenance,
and secrets all bind to this object — never to the plan. Plans propose; envelopes are
what actually get authority.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .approval import ApprovalGrant
from .capability import CapabilitySet
from .hashing import sha256_of
from .identity import Actor, DelegationChain, Principal
from .operation import Operation
from .provenance import ProvenanceRecord
from .runtime import Constraints, RuntimeContext


class Intent(BaseModel):
    """WHY: the task and purpose an action serves."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    purpose: str


class ActionEnvelope(BaseModel):
    """The canonical, resolved, authorizable unit of side effect."""

    model_config = ConfigDict(frozen=True)

    action_id: str
    principal: Principal
    actor: Actor
    delegation: DelegationChain
    intent: Intent
    operation: Operation
    capabilities: CapabilitySet
    provenance: ProvenanceRecord
    runtime: RuntimeContext
    constraints: Constraints
    approval: ApprovalGrant | None = None

    @property
    def action_hash(self) -> str:
        """Stable identity of the resolved action: who + what + where + params + ctx.

        This is what an approval binds to (INV-03) and what execution-time
        authorization decisions key on.
        """
        return sha256_of(
            {
                "actor": self.actor.model_dump(),
                "namespace": self.operation.namespace,
                "action": self.operation.action,
                "resource": self.operation.resource,
                "parameters_hash": self.operation.parameters_hash,
                "delegation": self.delegation.model_dump(),
                "tenant": self.principal.tenant,
                # INV-11: approval binds to the tool/skill definition, not just the op.
                "skill_digest": self.runtime.skill.digest if self.runtime.skill else None,
                "mcp_digest": (
                    self.runtime.mcp_server.digest if self.runtime.mcp_server else None
                ),
            }
        )

    def with_approval(self, grant: ApprovalGrant) -> "ActionEnvelope":
        return self.model_copy(update={"approval": grant})

    def with_operation(self, operation: Operation) -> "ActionEnvelope":
        return self.model_copy(update={"operation": operation})
