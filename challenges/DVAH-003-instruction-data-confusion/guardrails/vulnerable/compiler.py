"""VULNERABLE context compiler: flattens tool output into the instruction channel.

The bug (INV-06): untrusted observations are emitted as INSTRUCTION items with their
(untrusted) trust preserved, so a planted instruction in retrieved data is obeyed.
"""

from __future__ import annotations

from dvah.harness.compiler import INSTRUCTION, CompiledContext, ContextItem
from dvah.models.provenance import TrustLevel


class VulnerableContextCompiler:
    def compile(self, ctx):
        items = [
            ContextItem(
                channel=INSTRUCTION,
                trust=TrustLevel.USER_INSTRUCTION,
                source="user",
                content={"text": ctx.intent.purpose},
            )
        ]
        for obs in ctx.observations:
            # BUG: everything the agent saw becomes an instruction.
            items.append(
                ContextItem(
                    channel=INSTRUCTION, trust=obs.trust, source=obs.source,
                    content=obs.content,
                )
            )
        return CompiledContext(items=tuple(items))
