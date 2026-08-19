"""A tiny MCP-style tool server, spoken to over stdio by ``MCPToolProvider``.

Runs as a subprocess (``python -m dvah.providers.mcp_stub``) and answers one JSON
request per line with one JSON response per line. It is a *stand-in* for a real MCP
server: it performs NO network I/O — a ``fetch`` just echoes the requested host — so the
lab exercises a genuine process boundary deterministically and offline. The point of the
lab is that egress containment must be enforced by the HARNESS around this boundary, not
by trusting whatever the server on the other side does.
"""

from __future__ import annotations

import json
import sys

SERVER_ID = "mcp-stub-v1"


def _handle(req: dict) -> dict:
    if req.get("method") == "fetch":
        host = req.get("host", "")
        # No real socket — echo what a fetch *would* have retrieved from ``host``.
        return {"ok": True, "server_id": SERVER_ID, "host": host,
                "content": f"contents-of://{host}"}
    return {"ok": False, "server_id": SERVER_ID, "error": "unknown method"}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp = _handle(json.loads(line))
        except Exception as exc:  # never crash the transport on a bad frame
            resp = {"ok": False, "error": f"bad request: {exc}"}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
