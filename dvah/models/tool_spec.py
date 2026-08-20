"""Tool specification — the review-facing definition of one ``namespace.action`` tool.

Real agent platforms describe each tool with a ``name``/``description``/``input_schema``
(Anthropic tool-use) — here that shape is captured per operation, aligned to MCP's tool
``inputSchema`` (JSON Schema). This is **advisory metadata only**: it is what a runtime
would advertise to a model, but it never merges into ``Operation.parameters`` and so can
never perturb ``parameters_hash``/``action_hash``. The specs are held in a core, provider-
shared catalog keyed by ``id`` (``namespace.action``) because the concrete actions live in
the tool providers, not in any one lab.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ToolSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    namespace: str
    action: str
    name: str = ""
    description: str = ""
    #: JSON Schema for the tool's arguments (MCP ``inputSchema`` shape). Opaque data —
    #: advertised to models, never used for authorization.
    input_schema: dict = {}

    @property
    def id(self) -> str:
        return f"{self.namespace}.{self.action}"
