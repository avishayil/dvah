"""VULNERABLE skill loader: accepts the upgraded manifest wholesale (INV-07).

The bug: every requested permission is granted, the pinned digest is ignored, and no
permission-diff is produced — so a skill "update" silently widens capabilities.
"""

from __future__ import annotations

from dvah.models.capability import CapabilitySet
from dvah.security.skills import SkillLoadResult


class AutoAcceptSkillLoader:
    def load(self, manifest, approved_permissions, pinned_digest):
        # BUG: grant everything the manifest asks for; never flag expansion.
        return SkillLoadResult(
            granted=CapabilitySet(caps=frozenset(manifest.permissions)),
            expanded=(),
            trusted=True,
        )
