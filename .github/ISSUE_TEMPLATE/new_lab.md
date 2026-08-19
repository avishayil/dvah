---
name: New lab proposal
about: Propose a new DVAH lab / security invariant
title: "[lab] "
labels: lab, enhancement
---

### Invariant
Which security invariant does this teach? (existing INV-0X, or propose a new one with a
one-sentence statement.)

### The architectural failure
What does the vulnerable harness do wrong, and where (which swappable slot)?

### The fix
What must the learner change to restore the invariant?

### Exploit & proof
- Exploit: what unauthorized outcome does the bug enable?
- Invariant/property test: what must hold for *all* inputs?
- Adversarial mutation: what near-miss should defeat a too-narrow patch?

### Standards mapping
OWASP ASI / LLM Top 10 / NIST / MCP references, if any.
