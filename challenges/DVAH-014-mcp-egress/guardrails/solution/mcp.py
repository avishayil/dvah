"""FIXED tool boundary (INV-14).

The harness contains the runtime boundary: network egress is confined to an allowlist and
the tool server's identity is pinned. A ``fetch`` to any non-approved host is denied before
it crosses the boundary, regardless of what the plan or the server asks for.
"""

from __future__ import annotations

from dvah.providers.mcp_tools import MCPToolProvider


class ContainedMCPProvider(MCPToolProvider):
    allow_hosts = ("api.github.com",)  # egress confined to approved hosts
    verify_identity = True             # only the pinned tool server is trusted
