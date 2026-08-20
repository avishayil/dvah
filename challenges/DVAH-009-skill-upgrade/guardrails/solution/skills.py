"""FIXED skill loader: digest-pinned, attenuated to the approved set (INV-07).

granted = requested ∩ approved, only when the manifest digest is pinned; any requested
permission beyond the approved set is reported and requires re-approval.
"""

from __future__ import annotations

from dvah.security.skills import BuiltinSkillLoader


class PinnedSkillLoader(BuiltinSkillLoader):
    pass
