"""MCPToolProvider — a ToolProvider that reaches an MCP-style server over a real
process/stdio boundary (INV-14).

Each ``fetch`` opens a subprocess (``dvah.providers.mcp_stub``), sends one JSON request
and reads one JSON response over stdio — a genuine external boundary, but deterministic
and offline (the stub performs no network I/O). Because it is external, its output trust
is assigned by the harness (``is_external = True``), never inherited from the server.

Egress CONTAINMENT is the harness's job: ``allow_hosts`` is an allowlist enforced BEFORE
anything crosses the boundary. ``None`` means "no containment" (inherit unrestricted
egress) — the vulnerable posture. A bound server identity (``verify_identity``) rejects a
tool server that isn't the one we pinned.
"""

from __future__ import annotations

import json
import subprocess
import sys
from urllib.parse import urlparse

from ..models.operation import Operation
from ..models.provenance import TrustLevel
from .mcp_stub import SERVER_ID
from .tools import ToolResult


def _host_of(resource: str) -> str:
    """The network host a resource would egress to (scheme-less values are hosts)."""
    parsed = urlparse(resource)
    return parsed.netloc or parsed.path or resource


class MCPToolProvider:
    """Talks to an MCP stub over stdio. Records every host it actually reaches."""

    is_external = True
    #: Egress allowlist. ``None`` = unrestricted (no containment) — the vulnerable default.
    allow_hosts: tuple[str, ...] | None = None
    #: When True, reject a tool server whose identity isn't the pinned ``SERVER_ID``.
    verify_identity: bool = False

    def __init__(self) -> None:
        self.egress: list[str] = []   # hosts that actually crossed the boundary
        self.blocked: list[str] = []  # hosts denied by containment

    def supports(self, namespace: str) -> bool:
        return namespace == "mcp"

    def invoke(self, operation: Operation, credential: str | None = None) -> ToolResult:
        if operation.action != "fetch":
            return ToolResult(ok=False, output={"error": "unknown action"}, source="mcp")
        host = _host_of(operation.resource)
        src = f"mcp:{host}"

        # Containment is enforced by the harness BEFORE the boundary is crossed.
        if not self._egress_allowed(host):
            self.blocked.append(host)
            return ToolResult(ok=False, output={"error": "egress blocked", "host": host},
                              trust=TrustLevel.UNTRUSTED_DATA, source=src)

        resp = self._call_server({"method": "fetch", "host": host})

        if self.verify_identity and resp.get("server_id") != SERVER_ID:
            return ToolResult(ok=False, output={"error": "unrecognized tool server"},
                              trust=TrustLevel.UNTRUSTED_DATA, source=src)

        self.egress.append(host)  # the boundary was crossed to this host
        return ToolResult(ok=bool(resp.get("ok")),
                          output={"content": resp.get("content", "")},
                          trust=TrustLevel.UNTRUSTED_DATA, source=src)

    def _egress_allowed(self, host: str) -> bool:
        return self.allow_hosts is None or host in self.allow_hosts

    def _call_server(self, req: dict) -> dict:  # pragma: no cover - spawns the mcp_stub subprocess boundary
        proc = subprocess.Popen(
            [sys.executable, "-m", "dvah.providers.mcp_stub"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        try:
            out, _ = proc.communicate(json.dumps(req) + "\n", timeout=15)
        except Exception:
            if proc.poll() is None:
                proc.kill()
            return {"ok": False, "error": "transport failure"}
        line = next((ln for ln in out.splitlines() if ln.strip()), "{}")
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return {"ok": False, "error": "bad response"}
