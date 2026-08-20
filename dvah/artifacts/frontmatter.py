"""Split a Markdown document with optional YAML frontmatter into ``(meta, body)``.

The tiny, dependency-free convention shared by ``SKILL.md`` and ``agents/<id>.md``: an
opening ``---`` fence, a YAML block, a closing ``---`` fence, then the Markdown body. No
frontmatter → ``({}, text)``. Reuses the core ``pyyaml`` dep; no Markdown/frontmatter
library is pulled in.
"""

from __future__ import annotations

import yaml

_FENCE = "---"


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return ``(metadata, body)``. Raises ``ValueError`` on a malformed frontmatter block.

    Tolerates a leading BOM/whitespace-only lines and CRLF endings. A document that does
    not open with a ``---`` fence is treated as pure body with empty metadata.
    """
    normalized = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith(_FENCE + "\n") and normalized.strip() != _FENCE:
        return {}, text

    lines = normalized.split("\n")
    # lines[0] is the opening fence; find the closing fence.
    for idx in range(1, len(lines)):
        if lines[idx].strip() == _FENCE:
            block = "\n".join(lines[1:idx])
            body = "\n".join(lines[idx + 1 :])
            loaded = yaml.safe_load(block) if block.strip() else {}
            if loaded is not None and not isinstance(loaded, dict):
                raise ValueError("frontmatter must be a YAML mapping")
            return (loaded or {}), body.strip()

    raise ValueError("unterminated frontmatter: missing closing '---' fence")
