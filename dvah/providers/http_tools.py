"""HttpToolProvider — executes resolved operations against the FastAPI services.

Same ToolProvider contract and ToolResult shape as NativeToolProvider, but over HTTP.
Import-safe without a live server: a connection is only opened inside ``invoke``.
"""

from __future__ import annotations

import httpx

from ..models.operation import Operation
from ..models.provenance import TrustLevel
from .tools import ToolResult

DEFAULT_BASE_URLS = {
    "files": "http://127.0.0.1:8001",
    "github": "http://127.0.0.1:8002",
    "email": "http://127.0.0.1:8003",
    "cloud": "http://127.0.0.1:8004",
}


class HttpToolProvider:
    #: Crosses an external boundary — the harness assigns trust to its output (INV-14).
    is_external = True

    def __init__(self, base_urls: dict[str, str] | None = None, timeout: float = 5.0) -> None:
        self._base = {**DEFAULT_BASE_URLS, **(base_urls or {})}
        self._timeout = timeout

    def supports(self, namespace: str) -> bool:
        return namespace in self._base

    def invoke(self, operation: Operation, credential: str | None = None) -> ToolResult:
        handler = getattr(self, f"_do_{operation.namespace}", None)
        if handler is None:
            return ToolResult(ok=False, output={"error": "unknown namespace"})
        # The credential rides an Authorization header — transport-level plumbing, never
        # part of the operation body (so the executed operation == the authorized one).
        headers = {"Authorization": f"Bearer {credential}"} if credential else {}
        with httpx.Client(base_url=self._base[operation.namespace], timeout=self._timeout,
                          headers=headers) as client:
            return handler(client, operation)

    def _do_files(self, client: httpx.Client, op: Operation) -> ToolResult:
        source = f"files:{op.resource}"
        if op.action == "read":
            data = client.get("/files", params={"path": op.resource}).json()
            if not data.get("ok"):
                return ToolResult(ok=False, output={"error": "not found"}, source=source)
            return ToolResult(ok=True, output={"contents": data["contents"]},
                              trust=TrustLevel.UNTRUSTED_DATA, source=source)
        if op.action == "delete":
            data = client.request("DELETE", "/files", params={"path": op.resource}).json()
            return ToolResult(ok=data["ok"], output={}, source=source)
        if op.action == "rename":
            data = client.post("/files/rename",
                               json={"path": op.resource, "dest": op.parameters.get("dest", "")}).json()
            return ToolResult(ok=data["ok"], output={}, source=source)
        return ToolResult(ok=False, output={"error": "unknown action"}, source=source)

    def _do_github(self, client: httpx.Client, op: Operation) -> ToolResult:
        source = f"github:{op.resource}"
        if op.action == "issue.read":
            data = client.get("/github/issues", params={"repo": op.resource}).json()
            return ToolResult(ok=True, output={"issues": data.get("issues", [])},
                              trust=TrustLevel.UNTRUSTED_DATA, source=source)
        if op.action == "issue.comment":
            data = client.post("/github/comment",
                               json={"repo": op.resource, "issue": int(op.parameters.get("issue", 0)),
                                     "body": str(op.parameters.get("body", ""))}).json()
            return ToolResult(ok=data["ok"], output={}, source=source)
        if op.action == "repository.delete":
            data = client.request("DELETE", "/github/repo", params={"repo": op.resource}).json()
            return ToolResult(ok=data["ok"], output={}, source=source)
        return ToolResult(ok=False, output={"error": "unknown action"}, source=source)

    def _do_email(self, client: httpx.Client, op: Operation) -> ToolResult:
        source = f"email:{op.resource}"
        if op.action == "send":
            data = client.post("/email/send",
                               json={"to": op.parameters.get("to", op.resource),
                                     "subject": op.parameters.get("subject", ""),
                                     "body": op.parameters.get("body", "")}).json()
            return ToolResult(ok=data["ok"], output={"id": data.get("id")}, source=source)
        return ToolResult(ok=False, output={"error": "unknown action"}, source=source)

    def _do_cloud(self, client: httpx.Client, op: Operation) -> ToolResult:
        source = f"cloud:{op.resource}"
        if op.action == "instance.list":
            data = client.get("/cloud/instances").json()
            return ToolResult(ok=True, output={"instances": data.get("instances", [])},
                              trust=TrustLevel.UNTRUSTED_DATA, source=source)
        if op.action == "instance.terminate":
            data = client.post(f"/cloud/instances/{op.resource}/terminate").json()
            return ToolResult(ok=data["ok"], output={}, source=source)
        return ToolResult(ok=False, output={"error": "unknown action"}, source=source)
