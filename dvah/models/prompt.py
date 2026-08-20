"""Prompt layering — instructions as ordered config artifacts, not one mega-prompt.

The reference architecture layers instructions ``system → agent → skill → task``. DVAH's
runtime enforces instruction/data separation via trust *channels* in the context compiler; this
model captures the *authoring* layering that feeds the live model-facing prompt. ``render()``
affects only live model text — the deterministic oracle ignores it and nothing reaches
``action_hash``.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class PromptScope(str, Enum):
    SYSTEM = "system"
    AGENT = "agent"
    SKILL = "skill"
    TASK = "task"


#: Canonical layering order, outermost (most trusted/base) first.
SCOPE_ORDER = (PromptScope.SYSTEM, PromptScope.AGENT, PromptScope.SKILL, PromptScope.TASK)


class PromptLayer(BaseModel):
    model_config = ConfigDict(frozen=True)

    scope: PromptScope
    ref: str = ""
    text: str = ""


class PromptStack(BaseModel):
    model_config = ConfigDict(frozen=True)

    layers: tuple[PromptLayer, ...] = ()

    def render(self) -> str:
        """Concatenate non-empty layers in canonical ``system→agent→skill→task`` order."""
        order = {scope: i for i, scope in enumerate(SCOPE_ORDER)}
        ordered = sorted(self.layers, key=lambda layer: order.get(layer.scope, len(order)))
        return "\n\n".join(layer.text for layer in ordered if layer.text.strip())
