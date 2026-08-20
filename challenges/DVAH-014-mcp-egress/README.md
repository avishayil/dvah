# DVAH-014 — The Unbounded Tool Server (INV-14)

**Invariant:** INV-14 — *Runtime boundaries are contained: network egress and tool-server
identity are enforced by the harness, not inherited.*

Agents increasingly reach the world through **MCP servers** and other out-of-process tool
runtimes. Those runtimes have their own network reach. If your harness simply calls the
tool and trusts wherever it goes, a benign-looking `fetch` becomes a data-exfiltration and
SSRF primitive: the plan (or a compromised tool server) picks the destination, and traffic
leaves your trust boundary.

DVAH models a real boundary: `MCPToolProvider` (`dvah/providers/mcp_tools.py`) talks to an
MCP stub over a genuine subprocess/stdio channel. The stub does no real network I/O — it
echoes the requested host — so the lab is deterministic and offline, and the lesson is
about **where containment lives**, not about sockets.

## The bug

`vulnerable/mcp.py` inherits the tool's unrestricted posture: no egress allowlist
(`allow_hosts = None`) and no tool-server identity binding (`verify_identity = False`). A
`fetch` to `https://evil.example/exfil` crosses the boundary and the data is gone.

## Your job

Contain the boundary **in the harness**: confine egress to an allowlist of approved hosts
and pin the tool server's identity, so a fetch can only reach approved destinations no
matter what the plan or the server requests — including look-alike hostnames
(`api.github.com.evil.com`) and cloud metadata endpoints (`169.254.169.254`).

## Prove it

- **exploit** — a fetch to an attacker host must not cross the boundary.
- **invariant (INV-14)** — across a set of hosts, only allowlisted ones are ever reached.
- **adversarial** — the same holds for look-alike and SSRF-style destinations, so a fix
  that only blocks the demo host fails.

Also note the harness-level companion to this invariant: output that crosses an **external**
boundary has its trust **assigned by the harness** (`is_external` → downgraded to untrusted
data), so a tool server cannot declare its own output a trusted instruction.

## Artifacts
This lab ships an authored `agents/worker.md` (its `AgentDefinition` — frontmatter +
system prompt, with `capabilities` cross-validated against `environment/agents.yaml`) and a
`prompts/system.md` base instruction layer. These are advisory reference-architecture
overlays for the live/subagent path — nothing here reaches `action_hash` or changes the
security verdict.
