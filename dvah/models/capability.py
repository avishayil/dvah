"""Capability models.

A capability is a namespaced permission (``github``/``issue.comment``). Authorization
asks a ``CapabilitySet`` whether it *permits* a concrete operation. Delegation
attenuation (INV-02) is expressed as set operations over these.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Capability(BaseModel):
    """A single namespaced permission. ``action`` may be ``"*"`` (all in namespace)."""

    model_config = ConfigDict(frozen=True)

    namespace: str
    action: str

    def covers(self, op_namespace: str, op_action: str) -> bool:
        """True if this capability authorizes the given operation."""
        if self.namespace != op_namespace:
            return False
        return self.action == "*" or self.action == op_action


class CapabilitySet(BaseModel):
    """An immutable set of capabilities with the algebra delegation relies on."""

    model_config = ConfigDict(frozen=True)

    caps: frozenset[Capability] = frozenset()

    def permits(self, op_namespace: str, op_action: str) -> bool:
        return any(c.covers(op_namespace, op_action) for c in self.caps)

    def intersect(self, other: "CapabilitySet") -> "CapabilitySet":
        return CapabilitySet(caps=self.caps & other.caps)

    def issubset(self, other: "CapabilitySet") -> bool:
        return self.caps <= other.caps
