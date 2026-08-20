"""VULNERABLE policy: authorizes by tool namespace, not by operation (INV-13).

If the agent holds ANY capability in the operation's namespace, every operation in that
namespace is allowed — and the approval requirement is skipped entirely.
"""

from __future__ import annotations

from dvah.security.decision import Decision, Verdict


class ToolNamePolicy:
    def authorize(self, envelope) -> Decision:
        namespace = envelope.operation.namespace
        holds_tool = any(c.namespace == namespace for c in envelope.capabilities.caps)
        if holds_tool:
            # BUG: any operation in a permitted tool is allowed.
            return Decision(verdict=Verdict.ALLOW, reason=f"tool {namespace} permitted")
        return Decision(verdict=Verdict.DENY, reason=f"tool {namespace} not permitted",
                        invariant="INV-01")
