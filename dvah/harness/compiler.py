"""Context compiler — assembles the model's context from observations (INV-06).

The correct compiler keeps untrusted tool output in the DATA channel; it never
promotes retrieved data into the instruction channel. A vulnerable compiler that
flattens data into instructions is exactly how "data becomes instructions".
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from ..models.provenance import INSTRUCTION_TRUST_LEVELS, TrustLevel

INSTRUCTION = "instruction"
DATA = "data"


class ContextItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    channel: str  # "instruction" | "data"
    trust: TrustLevel
    source: str
    content: dict = {}


class CompiledContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[ContextItem, ...] = ()

    def has_untrusted_instruction(self) -> bool:
        """INV-06: no instruction-channel item may carry a non-instruction trust."""
        return any(
            item.channel == INSTRUCTION and item.trust not in INSTRUCTION_TRUST_LEVELS
            for item in self.items
        )

    def to_model_context(self) -> tuple[dict, ...]:
        return tuple(
            {
                "channel": item.channel,
                "trust": item.trust.value,
                "source": item.source,
                "content": item.content,
            }
            for item in self.items
        )


@runtime_checkable
class ContextCompiler(Protocol):
    def compile(self, ctx: "RunContext") -> CompiledContext: ...  # noqa: F821


class BuiltinContextCompiler:
    """Correct compiler: the task is the only instruction; data stays data."""

    def compile(self, ctx: "RunContext") -> CompiledContext:  # noqa: F821
        items = [
            ContextItem(
                channel=INSTRUCTION,
                trust=TrustLevel.USER_INSTRUCTION,
                source="user",
                content={"text": ctx.intent.purpose},
            )
        ]
        # Trusted-loaded skills contribute an instruction fragment + their tool schemas.
        # ``ctx.skills`` is empty for the 13 non-skill labs, so their context is unchanged.
        for skill in getattr(ctx, "skills", ()):
            if not skill.instructions and not skill.tools:
                continue
            items.append(
                ContextItem(
                    channel=INSTRUCTION,
                    trust=TrustLevel.TRUSTED_INSTRUCTION,
                    source=f"skill:{skill.name}",
                    content={"text": skill.instructions, "tools": list(skill.tools)},
                )
            )
        for obs in ctx.observations:
            items.append(
                ContextItem(
                    channel=DATA, trust=obs.trust, source=obs.source, content=obs.content
                )
            )
        return CompiledContext(items=tuple(items))
