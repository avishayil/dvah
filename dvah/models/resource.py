"""Resource — read-only knowledge/data exposed to an agent (the MCP "resource" primitive).

Distinct from ``environment`` *world state* (files/github the agent acts on via tools) and from
agent *memory*: a Resource is reference knowledge a skill or agent carries into context. It is
**advisory** and defaults to ``UNTRUSTED_DATA`` — retrieved knowledge is data, never a privileged
instruction (INV-06/INV-14). Nothing here reaches ``action_hash``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .provenance import TrustLevel


class Resource(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str = ""
    description: str = ""
    #: MIME type of the content (MCP resource ``mimeType``).
    mime_type: str = "text/plain"
    #: MCP-style locator; empty means the content is inline below.
    uri: str = ""
    #: Inline read-only content (optional; used when ``uri`` is empty).
    content: str = ""
    #: Retrieved knowledge is data by default, not an instruction.
    trust: TrustLevel = TrustLevel.UNTRUSTED_DATA
    #: Tenant scoping hint (aligns with INV-10 memory isolation); advisory.
    tenant: str = ""
    metadata: dict = {}
