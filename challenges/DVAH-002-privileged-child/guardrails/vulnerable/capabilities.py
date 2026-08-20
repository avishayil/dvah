"""VULNERABLE capability resolver: child inherits the global policy profile.

The bug (INV-02): ``parent`` and ``requested`` are ignored, so a subagent can become
strictly more privileged than the agent that spawned it.
"""

from __future__ import annotations


class VulnerableCapabilityResolver:
    def derive_child(self, requested, parent, policy):
        return policy  # BUG: ignores parent and requested — no attenuation
