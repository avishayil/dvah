# DVAH ↔ external security frameworks

DVAH's taxonomy is **invariant-based** and durable; this table maps each invariant/lab to
the current agent-security ecosystem so the labs stay legible to people who know those
frameworks. Mappings are **indicative, not normative** — DVAH's grading is driven by its
own invariant property + adversarial tests.

**Framework references used below**
- **OWASP ASI** — OWASP GenAI Security Project, *Agentic AI: Threats and Mitigations* (Agentic Security Initiative), threat taxonomy **T1–T15** (T1 Memory Poisoning, T2 Tool Misuse, T3 Privilege Compromise, T4 Resource Overload, T8 Repudiation/Untraceability, T10 Overwhelming HITL, T12 Agent Communication Poisoning, …).
- **OWASP LLM** — *OWASP Top 10 for LLM Applications (2025)* (LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure, LLM06 Excessive Agency, …).
- **AAI** — the community *OWASP Agentic AI Top 10* ids (e.g. AAI001 Authorization/Control Hijacking, AAI006 Memory/Context Manipulation, AAI011 Untraceability). Community-maintained; cross-reference only.
- **NHI (aspirational)** — non-human / agent identity guidance: **CSA — IAM for Agentic AI** and **NIST AI 600-1 (Generative AI Profile)**. There is no finalized NIST "agent identity & authorization" standard as of this writing; treat this column as directional.
- **MCP** — *Model Context Protocol — Security Best Practices* (audience-bound tokens, per-client consent, no token passthrough, trust-boundary/accountability guidance).

| Lab | DVAH invariant | OWASP (ASI / LLM) | Non-human identity (NHI, aspirational) | MCP security |
|-----|----------------|-------------------|----------------------------------------|--------------|
| 001 | INV-01 execution-time authorization | LLM06 Excessive Agency; ASI T3 | authorization bound to action time | consent per action |
| 002 | INV-02 delegation attenuation | ASI T3 Privilege Compromise | scoped non-human identity / least privilege | audience-bound authorization |
| 003 | INV-06 instruction/data | LLM01 Prompt Injection; ASI T2 | prompt/data provenance | untrusted resource content isn't instructions |
| 004 | INV-04 secrets isolation | LLM02 Sensitive Info Disclosure | credential custody off the model path | avoid token passthrough |
| 005 | INV-05 provenance | ASI T8 Repudiation/Untraceability; AAI011 | provenance for policy decisions | accountability across trust boundaries |
| 006 | INV-06 budget | ASI T4 Resource Overload | resource authorization | long-running task scoping |
| 007 | INV-03 approval binding | ASI T10 Overwhelming HITL; complete mediation | authorization binding to a decision | per-client consent |
| 008 | INV-13 operation-granular authorization | LLM06 Excessive Agency; ASI T3 | fine-grained, per-operation authorization | least privilege |
| 009 | INV-07 skill capability stability | ASI T2 Tool Misuse (supply chain) | signed/pinned capability grants | tool/skill integrity + version pinning |
| 010 | INV-09 continuous authz / revocation | ASI T3; temporal authorization | identity lifecycle + revocation propagation | token lifetime / revocation |
| 011 | INV-10 memory isolation | ASI T1 Memory Poisoning; AAI006 | tenant isolation of agent memory | cross-tenant data isolation |
| 012 | INV-11 tool-definition binding | ASI T2 / T12 Agent Comms Poisoning | verify tool identity/version | server identity substitution / tool integrity |
| 013 | INV-12 atomic decisions (no race) | ASI T4 (race bypass); complete mediation | atomic authorization decisions | — |
| 014 | INV-14 runtime boundary containment | LLM06 Excessive Agency; SSRF; ASI (tool/network isolation) | egress allowlisting, tool-server identity, network segmentation | least privilege; contain untrusted boundaries |

> These are cross-references for orientation, not a compliance claim. Framework documents
> evolve; verify against the primary source before citing DVAH as evidence of coverage.

## Artifact formats ↔ Anthropic / MCP

DVAH represents skills, agents, and tools as real-world **artifact files** that parse into
the frozen Pydantic models — following Anthropic / Claude Code conventions and
cross-referenced to MCP — so a lab reads like the platforms it teaches. As with the
invariant table, these mappings are **indicative, not normative**: the file shapes track
current conventions for legibility, not conformance. Crucially, all of this metadata is
**advisory** — root capabilities still come from `environment/agents.yaml` + plan-step
params, and none of it (descriptions, system-prompt bodies, `input_schema`) reaches
`action_hash`.

| DVAH artifact | Anthropic / Claude Code analog | MCP analog |
|---------------|-------------------------------|------------|
| `SKILL.md` frontmatter + Markdown body (`name`/`description`/`allowed-tools` + instructions) | Anthropic **Agent Skills** (SKILL.md `name`/`description`/`allowed-tools` + body) | packaged capability with an advertised description |
| `requested-permissions` (request ≠ grant, INV-07) | skill capability grants — requesting is not granting | least privilege + explicit user consent |
| `agents/<id>.md` (`name`/`description`/`model`/`tools` + system-prompt body) | Claude Code **subagent definition** (frontmatter + system prompt) | scoped client/agent identity |
| `ToolSpec.input_schema` (per `namespace.action`, JSON Schema) | Anthropic tool-use `input_schema` | MCP tool `inputSchema` (JSON Schema) |
| `ToolSpec` governance fields (`side_effect` read\|write\|destructive, `requires_approval`, `timeout_s`, `audit`) | tool risk/approval metadata advertised to the model | tool annotations (read-only / destructive hints) |
| `Resource` (`dvah/models/resource.py`; read-only knowledge, untrusted-by-default) | reference knowledge a skill/agent carries into context | MCP **resource** (`uri`/`mimeType`, read-only content) |
| `Workflow` / `WorkflowStep` (descriptive view of `plans.yaml`, not executed) | orchestration between steps (code-driven vs LLM-driven) | orchestration over tool/resource calls |
| `PromptStack` (layered `system → agent → skill → task`) | layered instructions (system prompt + agent + skill + task) | trust-boundary layering of instruction sources |
| `mcp` / `network` / `secrets` declarations | credential custody off the model path (no passthrough) | audience-bound tokens; no token passthrough |

> Same disclaimer as above: these are orientation cross-references, not a compliance claim.
> The artifact metadata is advertised to models but never authorizes an action.
