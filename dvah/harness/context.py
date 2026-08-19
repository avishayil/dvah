"""RunContext — the immutable execution state threaded through a task.

Carries WHO/WHY/WITH-WHAT-CAPS/UNDER-WHAT-LIMITS for the current agent instance.
Every mutation returns a new copy (immutability), so a subagent's context can never
retroactively alter its parent's.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..models.approval import ApprovalGrant
from ..models.capability import CapabilitySet
from ..models.envelope import Intent
from ..models.identity import Actor, DelegationChain, Principal
from ..models.observation import Observation
from ..models.provenance import ProvenanceRecord
from ..models.runtime import Constraints, RuntimeContext
from ..models.skill import SkillManifest


@dataclass(frozen=True)
class RunContext:
    principal: Principal
    actor: Actor
    delegation: DelegationChain
    intent: Intent
    capabilities: CapabilitySet
    constraints: Constraints
    runtime: RuntimeContext
    provenance: ProvenanceRecord = ProvenanceRecord()
    grants: tuple[ApprovalGrant, ...] = ()
    observations: tuple[Observation, ...] = ()
    actions_used: int = 0
    #: Skills attached to this agent (trusted-loaded only). Empty for the 13 non-skill
    #: labs → their compiled context is unchanged. The compiler injects each skill's
    #: instruction fragment when present.
    skills: tuple[SkillManifest, ...] = ()

    def with_observation(self, observation: Observation) -> "RunContext":
        return replace(self, observations=self.observations + (observation,))

    def with_skill(self, skill: SkillManifest) -> "RunContext":
        return replace(self, skills=self.skills + (skill,))

    def next_action_id(self) -> str:
        return f"act-d{self.delegation.depth}-{self.actions_used}"

    def tick(self) -> "RunContext":
        return replace(self, actions_used=self.actions_used + 1)

    def with_provenance(self, provenance: ProvenanceRecord) -> "RunContext":
        return replace(self, provenance=provenance)

    def with_grant(self, grant: ApprovalGrant) -> "RunContext":
        return replace(self, grants=self.grants + (grant,))

    def find_grant(self, action_hash: str) -> ApprovalGrant | None:
        for grant in self.grants:
            if grant.approved_action_hash == action_hash:
                return grant
        return None

    def child(
        self, agent_id: str, instance_id: str, capabilities: CapabilitySet
    ) -> "RunContext":
        """Spawn a subagent context: extended chain, fresh action count, new caps."""
        return replace(
            self,
            actor=Actor(agent_id=agent_id, instance_id=instance_id),
            delegation=self.delegation.extend(agent_id),
            capabilities=capabilities,
            grants=(),
            observations=(),
            actions_used=0,
        )
