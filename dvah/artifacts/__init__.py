"""Artifact parsers — read real-world artifact files into the frozen runtime models.

``SKILL.md`` → ``SkillManifest``, ``agents/<id>.md`` → ``AgentDefinition``, and the core
tool catalog (``dvah/tools/catalog/*.yaml``) → ``ToolSpec``. Parsing is behavior, so it
lives here rather than in ``models/``. Every parser raises with the offending path.
"""

from .agent_md import load_agent
from .frontmatter import split_frontmatter
from .prompt import load_prompts
from .resource_yaml import load_resources
from .skill_md import load_skill
from .tool_catalog import builtin_catalog, load_catalog_file, overlay
from .workflow_yaml import load_workflows

__all__ = [
    "split_frontmatter",
    "load_skill",
    "load_agent",
    "load_resources",
    "load_workflows",
    "load_prompts",
    "builtin_catalog",
    "load_catalog_file",
    "overlay",
]
