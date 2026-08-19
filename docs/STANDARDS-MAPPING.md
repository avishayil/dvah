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
