"""FIXED context compiler: retrieved data stays in the data channel (INV-06)."""

from __future__ import annotations

from dvah.harness.compiler import DATA, INSTRUCTION, CompiledContext, ContextItem
from dvah.models.provenance import TrustLevel


class TrustTaggingContextCompiler:
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
            items.append(
                ContextItem(
                    channel=DATA, trust=obs.trust, source=obs.source, content=obs.content
                )
            )
        return CompiledContext(items=tuple(items))
