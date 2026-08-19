"""Tool provider protocol — the boundary to external systems.

A provider executes a resolved Operation and returns a ToolResult that carries the
provenance (source + trust) of whatever it produced, so INV-05/06 can be enforced.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from ..models.operation import Operation
from ..models.provenance import TrustLevel


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ok: bool
    output: dict = {}
    trust: TrustLevel = TrustLevel.UNTRUSTED_DATA
    source: str = ""


@runtime_checkable
class ToolProvider(Protocol):
    #: True if the provider crosses an EXTERNAL boundary (network / subprocess / another
    #: runtime). The harness assigns trust to an external provider's output rather than
    #: believing ``ToolResult.trust`` (INV-14). First-party in-process providers set False.
    is_external: bool = False

    def supports(self, namespace: str) -> bool: ...
    # ``credential`` is an opaque execution-time handle (INV-04) supplied out-of-band by
    # the secret broker — it must NOT be read from / written to ``operation.parameters``.
    def invoke(self, operation: Operation, credential: str | None = None) -> ToolResult: ...
