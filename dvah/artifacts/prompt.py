"""Assemble layered PromptStacks (system → agent → skill → task) per agent.

Advisory: this describes how a live model's prompt is layered from config artifacts, replacing
the mega-prompt anti-pattern. The deterministic oracle ignores prompts entirely.

Layer sources, in order:
- SYSTEM: an optional ``prompts/system.md`` (the lab's base/harness instruction).
- AGENT:  the ``AgentDefinition.instructions`` body (from ``agents/<id>.md``).
- TASK:   the goal prompt(s) from ``environment/tasks.yaml`` addressed to that agent.
(SKILL layers are contributed at load time by attached skills, not pre-assembled here.)
"""

from __future__ import annotations

from pathlib import Path

from ..models.prompt import PromptLayer, PromptScope, PromptStack


def load_prompts(challenge_dir: str | Path, agent_defs: dict, tasks: dict) -> dict[str, PromptStack]:
    """Return ``{agent_id: PromptStack}`` for each declared agent (empty if no agents)."""
    challenge_dir = Path(challenge_dir)
    system_md = challenge_dir / "prompts" / "system.md"
    system_text = system_md.read_text().strip() if system_md.exists() else ""

    stacks: dict[str, PromptStack] = {}
    for agent_id, agent in agent_defs.items():
        layers = []
        if system_text:
            layers.append(PromptLayer(scope=PromptScope.SYSTEM, ref="prompts/system.md",
                                      text=system_text))
        instructions = getattr(agent, "instructions", "") or ""
        if instructions.strip():
            layers.append(PromptLayer(scope=PromptScope.AGENT, ref=f"agents/{agent_id}.md",
                                      text=instructions.strip()))
        for task_id, entry in (tasks or {}).items():
            if isinstance(entry, dict) and entry.get("prompt") and (
                entry.get("agent") in (None, agent_id)
                or entry.get("agent") == getattr(agent, "name", "")
            ):
                layers.append(PromptLayer(scope=PromptScope.TASK, ref=f"tasks/{task_id}",
                                          text=str(entry["prompt"]).strip()))
        stacks[agent_id] = PromptStack(layers=tuple(layers))
    return stacks
