"""Prompts layer — layered instructions (the reference "Prompt/Instructions" primitive).

The layering model lives in ``dvah.models.prompt`` (PromptStack: system→agent→skill→task);
``dvah.artifacts.prompt`` assembles per-agent stacks from the lab's files. Advisory for the
live model path; the deterministic oracle ignores it. This package is the domain home.
"""

from ..artifacts.prompt import load_prompts
from ..models.prompt import PromptLayer, PromptScope, PromptStack

__all__ = ["PromptStack", "PromptLayer", "PromptScope", "load_prompts"]
