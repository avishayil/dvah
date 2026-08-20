"""Skill loader (INV-07): a skill upgrade cannot silently expand capabilities.

The correct loader grants only permissions inside the *approved* set (and only when the
manifest digest matches the pinned one), and reports any permissions the upgraded
manifest requests beyond what was approved — those require explicit re-approval.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..models.capability import Capability, CapabilitySet
from ..models.skill import SkillManifest


@dataclass(frozen=True)
class SkillLoadResult:
    granted: CapabilitySet
    #: permissions the manifest requested beyond the approved set (need re-approval)
    expanded: tuple[Capability, ...]
    #: whether the manifest digest matched the pinned/approved digest
    trusted: bool

    @property
    def requires_reapproval(self) -> bool:
        return bool(self.expanded) or not self.trusted


@runtime_checkable
class SkillLoader(Protocol):
    def load(
        self,
        manifest: SkillManifest,
        approved_permissions: tuple[Capability, ...],
        pinned_digest: str | None,
    ) -> SkillLoadResult: ...


class BuiltinSkillLoader:
    """Correct loader: grant = requested ∩ approved (and only if the digest is pinned)."""

    def load(
        self,
        manifest: SkillManifest,
        approved_permissions: tuple[Capability, ...],
        pinned_digest: str | None,
    ) -> SkillLoadResult:
        approved = set(approved_permissions)
        requested = set(manifest.permissions)
        trusted = pinned_digest is None or manifest.digest == pinned_digest
        granted = (requested & approved) if trusted else set()
        expanded = tuple(
            sorted(requested - approved, key=lambda c: (c.namespace, c.action))
        )
        return SkillLoadResult(
            granted=CapabilitySet(caps=frozenset(granted)),
            expanded=expanded,
            trusted=trusted,
        )
