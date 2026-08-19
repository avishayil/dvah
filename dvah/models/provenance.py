"""Provenance models — BASED ON WHAT dimension.

Every piece of context carries where it came from and how much it should be trusted.
Preserving these tags across hops is INV-05; refusing to treat untrusted data as
instructions is INV-06.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class TrustLevel(str, Enum):
    TRUSTED_INSTRUCTION = "trusted_instruction"
    USER_INSTRUCTION = "user_instruction"
    UNTRUSTED_DATA = "untrusted_data"
    TOOL_METADATA = "tool_metadata"
    MEMORY = "memory"


#: Trust levels that are permitted to carry executable instructions.
INSTRUCTION_TRUST_LEVELS = frozenset(
    {TrustLevel.TRUSTED_INSTRUCTION, TrustLevel.USER_INSTRUCTION}
)


class ProvenanceTag(BaseModel):
    """Where a single piece of context came from and its trust classification."""

    model_config = ConfigDict(frozen=True)

    source: str
    trust: TrustLevel
    tenant: str
    timestamp: str  # ISO-8601, injected by the caller — never wall-clock here
    integrity: str | None = None


class ProvenanceRecord(BaseModel):
    """The provenance accumulated for an action: instruction vs data sources."""

    model_config = ConfigDict(frozen=True)

    instruction_sources: tuple[ProvenanceTag, ...] = ()
    data_sources: tuple[ProvenanceTag, ...] = ()

    def with_data(self, tag: ProvenanceTag) -> "ProvenanceRecord":
        return self.model_copy(update={"data_sources": self.data_sources + (tag,)})

    def with_instruction(self, tag: ProvenanceTag) -> "ProvenanceRecord":
        return self.model_copy(
            update={"instruction_sources": self.instruction_sources + (tag,)}
        )
