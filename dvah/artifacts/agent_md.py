"""Parse an ``agents/<id>.md`` (Claude Code subagent shape) into an ``AgentDefinition``.

Frontmatter: ``name``/``description``/``model`` → same; ``tools`` or ``allowed-tools`` →
``tools``; ``capabilities`` (list of ``{namespace, action}``) → ``capabilities``;
``delegation:{allowed, max_depth}`` → ``Delegation``; ``skills`` → ``skills``. The Markdown
body becomes the system-prompt ``instructions``. ``agent_id`` defaults to the filename stem.
"""

from __future__ import annotations

from pathlib import Path

from ..models.agent import AgentDefinition, Delegation
from ._common import as_capabilities, as_str_tuple
from .frontmatter import split_frontmatter


def load_agent(path: str | Path) -> AgentDefinition:
    path = Path(path)
    try:
        meta, body = split_frontmatter(path.read_text())
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc

    raw_delegation = meta.get("delegation") or {}
    if not isinstance(raw_delegation, dict):
        raise ValueError(f"{path}: 'delegation' must be a mapping")
    delegation = Delegation(
        allowed=bool(raw_delegation.get("allowed", False)),
        max_depth=int(raw_delegation.get("max_depth", 0)),
    )
    return AgentDefinition(
        agent_id=str(meta.get("agent_id") or path.stem),
        name=str(meta.get("name", "")),
        description=str(meta.get("description", "")),
        model=str(meta.get("model", "")),
        tools=as_str_tuple(meta.get("tools") or meta.get("allowed-tools")),
        capabilities=as_capabilities(meta.get("capabilities")),
        delegation=delegation,
        skills=as_str_tuple(meta.get("skills")),
        instructions=body,
    )
