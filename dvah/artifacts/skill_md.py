"""Parse a ``SKILL.md`` (Anthropic Agent Skills shape) into a ``SkillManifest``.

Frontmatter maps as: ``name``/``description``/``version``/``digest`` → same; ``allowed-tools``
→ ``tools``; ``requested-permissions`` (list of ``{namespace, action}``) → ``permissions``;
``mcp``/``network``/``secrets`` → same. The Markdown body becomes ``instructions``.
"""

from __future__ import annotations

from pathlib import Path

from ..models.skill import SkillManifest
from ._common import as_capabilities, as_str_tuple
from .frontmatter import split_frontmatter


def load_skill(path: str | Path) -> SkillManifest:
    path = Path(path)
    try:
        meta, body = split_frontmatter(path.read_text())
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not meta.get("name"):
        raise ValueError(f"{path}: SKILL.md frontmatter must define 'name'")
    return SkillManifest(
        name=meta["name"],
        digest=str(meta.get("digest", "")),
        permissions=as_capabilities(meta.get("requested-permissions")),
        version=str(meta.get("version", "")),
        description=str(meta.get("description", "")),
        instructions=body,
        tools=as_str_tuple(meta.get("allowed-tools")),
        mcp=as_str_tuple(meta.get("mcp")),
        network=as_str_tuple(meta.get("network")),
        secrets=as_str_tuple(meta.get("secrets")),
    )
