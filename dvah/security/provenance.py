"""Provenance tracker (INV-05 preservation, INV-06 instruction/data separation).

The correct default tags every tool output with its source and trust level, merges
tags without dropping them, and reports when untrusted data has leaked into the
instruction channel. Timestamps are injected so the harness stays deterministic.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.provenance import (
    INSTRUCTION_TRUST_LEVELS,
    ProvenanceRecord,
    ProvenanceTag,
    TrustLevel,
)


@runtime_checkable
class ProvenanceTracker(Protocol):
    def tag_tool_output(
        self, source: str, trust: TrustLevel, tenant: str, timestamp: str
    ) -> ProvenanceTag: ...
    def merge(self, record: ProvenanceRecord, tag: ProvenanceTag) -> ProvenanceRecord: ...
    def has_untrusted_instruction(self, record: ProvenanceRecord) -> bool: ...


class BuiltinProvenanceTracker:
    """Correct reference tracker: never silently drops or upgrades provenance."""

    def tag_tool_output(
        self, source: str, trust: TrustLevel, tenant: str, timestamp: str
    ) -> ProvenanceTag:
        return ProvenanceTag(
            source=source, trust=trust, tenant=tenant, timestamp=timestamp
        )

    def merge(self, record: ProvenanceRecord, tag: ProvenanceTag) -> ProvenanceRecord:
        if tag.trust in INSTRUCTION_TRUST_LEVELS:
            return record.with_instruction(tag)
        return record.with_data(tag)

    def has_untrusted_instruction(self, record: ProvenanceRecord) -> bool:
        return any(
            tag.trust not in INSTRUCTION_TRUST_LEVELS
            for tag in record.instruction_sources
        )
