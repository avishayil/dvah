"""NativeToolProvider — in-process execution of resolved operations (M1).

Maps ``namespace.action`` to a backend store method. Returns a ToolResult tagged as
untrusted data (external system output), which the broker feeds to provenance.
"""

from __future__ import annotations

from ..models.operation import Operation
from ..models.provenance import TrustLevel
from ..services.world_state import FileStore, GithubStore
from .tools import ToolResult


class NativeToolProvider:
    """Executes operations against in-memory service stores."""

    #: First-party, in-process provider — its results MAY assert their own trust level.
    is_external = False

    def __init__(self, files: FileStore, github: GithubStore) -> None:
        self._files = files
        self._github = github

    def supports(self, namespace: str) -> bool:
        return namespace in {"files", "github"}

    def invoke(self, operation: Operation, credential: str | None = None) -> ToolResult:
        # In-process stores need no credential; it is accepted to satisfy the contract
        # and is deliberately never merged into the operation.
        handler = getattr(self, f"_do_{operation.namespace}", None)
        if handler is None:
            return ToolResult(ok=False, output={"error": "unknown namespace"})
        return handler(operation)

    def _do_files(self, op: Operation) -> ToolResult:
        source = f"files:{op.resource}"
        if op.action == "read":
            if not self._files.exists(op.resource):
                return ToolResult(ok=False, output={"error": "not found"}, source=source)
            return ToolResult(
                ok=True,
                output={"contents": self._files.read(op.resource)},
                trust=TrustLevel.UNTRUSTED_DATA,
                source=source,
            )
        if op.action == "delete":
            return ToolResult(
                ok=self._files.delete(op.resource), output={}, source=source
            )
        if op.action == "rename":
            dest = op.parameters.get("dest", "")
            return ToolResult(
                ok=self._files.rename(op.resource, dest), output={}, source=source
            )
        return ToolResult(ok=False, output={"error": "unknown action"}, source=source)

    def _do_github(self, op: Operation) -> ToolResult:
        source = f"github:{op.resource}"
        if op.action == "issue.read":
            return ToolResult(
                ok=True,
                output={"issues": self._github.list_issues(op.resource)},
                trust=TrustLevel.UNTRUSTED_DATA,
                source=source,
            )
        if op.action == "issue.comment":
            issue = int(op.parameters.get("issue", 0))
            body = str(op.parameters.get("body", ""))
            return ToolResult(
                ok=self._github.comment(op.resource, issue, body),
                output={},
                source=source,
            )
        if op.action == "repository.delete":
            return ToolResult(
                ok=self._github.delete_repository(op.resource), output={}, source=source
            )
        return ToolResult(ok=False, output={"error": "unknown action"}, source=source)
