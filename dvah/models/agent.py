"""Agent definition — the declared identity + shape of an agent (an ``agents/<id>.md``).

This mirrors a real agent-platform definition (a Claude Code subagent ``.md``: frontmatter
``name``/``description``/``model``/``tools`` + a system-prompt body). It is **descriptive
metadata for the live/subagent path** — the deterministic oracle sources root capabilities
from ``environment/agents.yaml`` and subagent caps from plan-step params, so nothing here
reaches ``action_hash``. The loader cross-validates that ``capabilities`` matches the
``agents.yaml`` root, keeping the two representations honest without changing authorization.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .capability import Capability


class Delegation(BaseModel):
    model_config = ConfigDict(frozen=True)

    #: May this agent spawn subagents at all?
    allowed: bool = False
    #: Maximum delegation depth this agent is permitted (INV-06 budget is enforced
    #: independently at runtime from the plan step; this is the declared intent).
    max_depth: int = 0


class AgentDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    name: str = ""
    description: str = ""
    #: Provider/profile hint (``balanced``/``smart``/``cheap``/``local`` or a provider
    #: label). Advisory — the actual session provider comes from ``scenario.yaml``.
    model: str = ""
    #: Dotted tool identifiers this agent may call (``allowed-tools``).
    tools: tuple[str, ...] = ()
    #: The agent's own capabilities (must equal the ``agents.yaml`` root caps).
    capabilities: tuple[Capability, ...] = ()
    delegation: Delegation = Delegation()
    #: Names of skills this agent may load.
    skills: tuple[str, ...] = ()
    #: The system-prompt body (Markdown), injected only on the live path.
    instructions: str = ""
