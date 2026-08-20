"""Skill manifest — the declared identity + runtime shape of a loadable skill (INV-07/11).

A skill is a runtime object an agent loads: it contributes *instructions* and *tools* and
declares the *permissions/mcp/network/secrets* it needs. A skill upgrade must not silently
widen what an agent can do — the manifest carries a content ``digest`` (so approval can pin
a version) and the capabilities it *requests* (which are never granted beyond the agent's
own approved set; see ``dvah.security.skills``).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .capability import Capability


class SkillManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    digest: str
    #: Capabilities the skill REQUESTS. Requesting is not granting — the loader intersects
    #: these with the approved/agent set (INV-07). Kept named ``permissions`` for back-compat.
    permissions: tuple[Capability, ...] = ()

    # --- runtime shape (all optional; back-compat: SkillManifest(name, digest, permissions)) ---
    version: str = ""
    #: One-line summary (SKILL.md frontmatter ``description``) — used for review/triage
    #: legibility; advisory only, never reaches authorization.
    description: str = ""
    #: An instruction fragment injected into the model context when the skill loads trusted.
    instructions: str = ""
    #: Tool/operation identifiers the skill contributes (e.g. "github.issue.comment").
    tools: tuple[str, ...] = ()
    #: Declared runtime requirements (surfaced for review; not auto-granted).
    mcp: tuple[str, ...] = ()
    network: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()

    @property
    def requested_permissions(self) -> tuple[Capability, ...]:
        """Alias — a skill *requests* permissions; it does not thereby gain them."""
        return self.permissions
