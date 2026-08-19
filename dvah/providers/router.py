"""ToolRouter — a ToolProvider that multiplexes several sub-providers by namespace.

The harness has a single ``tools`` slot and the broker calls one ``cfg.tools.invoke(...)``.
The router lets a lab use MANY providers at once (e.g. native in-process tools AND a real
MCP subprocess) by dispatching each operation to the first sub-provider whose
``supports(namespace)`` is true.

INV-14 subtlety: "is this an external boundary?" is a PER-NAMESPACE fact, not a single flag
for the whole router. A native ``files`` op is first-party; an ``mcp`` op crosses a process
boundary. So the router exposes ``is_external_for(namespace)`` (and ``provider_for``), and the
broker consults that per operation — a native result keeps its trust, an MCP result is
downgraded. ``is_external`` is kept as a conservative flat fallback (True if ANY sub is
external) for code paths that don't ask per-namespace.
"""

from __future__ import annotations

from ..models.operation import Operation
from .tools import ToolProvider, ToolResult


class ToolRouter:
    """Dispatches an operation to the first registered provider that supports it."""

    def __init__(self, providers: tuple[ToolProvider, ...] | list[ToolProvider]) -> None:
        self._providers = tuple(providers)
        # Conservative flat fallback; the broker prefers per-namespace is_external_for().
        self.is_external = any(getattr(p, "is_external", False) for p in self._providers)

    @property
    def providers(self) -> tuple[ToolProvider, ...]:
        return self._providers

    def provider_for(self, namespace: str) -> ToolProvider | None:
        for p in self._providers:
            if p.supports(namespace):
                return p
        return None

    def is_external_for(self, namespace: str) -> bool:
        """Whether the sub-provider that would handle ``namespace`` crosses an external
        boundary (INV-14). Unknown namespaces are treated as non-external (they error on
        invoke anyway)."""
        p = self.provider_for(namespace)
        return bool(getattr(p, "is_external", False)) if p is not None else False

    def supports(self, namespace: str) -> bool:
        return self.provider_for(namespace) is not None

    def invoke(self, operation: Operation, credential: str | None = None) -> ToolResult:
        provider = self.provider_for(operation.namespace)
        if provider is None:
            return ToolResult(
                ok=False,
                output={"error": f"no tool provider for namespace {operation.namespace!r}"},
                source=f"router:{operation.namespace}",
            )
        return provider.invoke(operation, credential)
