"""Capability resolver — delegation attenuation (INV-02).

The correct child capability set is the intersection of what the child requested,
what the parent already holds, and what policy grants that child role. A child can
never exceed its parent.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.capability import CapabilitySet


@runtime_checkable
class CapabilityResolver(Protocol):
    def derive_child(
        self,
        requested: CapabilitySet,
        parent: CapabilitySet,
        policy: CapabilitySet,
    ) -> CapabilitySet: ...


class BuiltinCapabilityResolver:
    """Correct reference resolver: child = requested ∩ parent ∩ policy."""

    def derive_child(
        self,
        requested: CapabilitySet,
        parent: CapabilitySet,
        policy: CapabilitySet,
    ) -> CapabilitySet:
        return requested.intersect(parent).intersect(policy)
