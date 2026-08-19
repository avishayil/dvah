"""Identity and delegation models.

These answer the WHO dimension of an action: the human principal, the acting agent
instance, and the full delegation chain that led to the action (INV-08).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class Principal(BaseModel):
    """The human (or root non-human) principal on whose behalf work happens."""

    model_config = ConfigDict(frozen=True)

    user: str
    tenant: str


class Actor(BaseModel):
    """The specific agent instance performing an action."""

    model_config = ConfigDict(frozen=True)

    agent_id: str
    instance_id: str


class DelegationChain(BaseModel):
    """Ordered lineage of agents from the root principal to the current actor."""

    model_config = ConfigDict(frozen=True)

    root_principal: str
    chain: tuple[str, ...] = ()
    depth: int = 0

    @model_validator(mode="after")
    def _consistent(self) -> "DelegationChain":
        """Attribution must be internally well-formed — a malformed chain can't exist.

        Structural correspondence to the principal/actor is checked by the policy
        (INV-08); this guards the chain's own consistency so that an attribution
        invariant never has to trust a caller-supplied ``depth``/``chain`` pairing. A
        deliberately-forged chain (for a defeat or test) must be built via
        ``model_construct`` to bypass this.
        """
        if not self.root_principal:
            raise ValueError("delegation chain requires a non-empty root_principal")
        if not self.chain:
            raise ValueError("delegation chain must contain at least the acting agent")
        if self.depth != len(self.chain) - 1:
            raise ValueError(
                f"delegation depth {self.depth} inconsistent with "
                f"chain length {len(self.chain)} (expected {len(self.chain) - 1})"
            )
        return self

    def extend(self, child_agent_id: str) -> "DelegationChain":
        """Return a new chain with ``child_agent_id`` appended and depth incremented."""
        return DelegationChain(
            root_principal=self.root_principal,
            chain=self.chain + (child_agent_id,),
            depth=self.depth + 1,
        )
