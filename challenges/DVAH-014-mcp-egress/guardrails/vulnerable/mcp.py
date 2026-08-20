"""VULNERABLE tool boundary (INV-14).

The MCP tool server reaches whatever host the plan/server names — the harness inherits
the tool's network posture instead of containing it. There is no egress allowlist and no
tool-server identity binding, so a ``fetch`` to an attacker host succeeds and data leaves
across an uncontained boundary.
"""

from __future__ import annotations

from dvah.providers.mcp_tools import MCPToolProvider


class InheritedEgressMCPProvider(MCPToolProvider):
    allow_hosts = None       # BUG: no containment — any host is reachable
    verify_identity = False  # BUG: any tool server is trusted
