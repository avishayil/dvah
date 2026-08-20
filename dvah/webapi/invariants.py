"""Parse invariant statements from ``docs/INVARIANTS.md`` (single source of truth)."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_DOCS = Path(__file__).resolve().parent.parent.parent / "docs" / "INVARIANTS.md"
_ROW = re.compile(r"^\|\s*(INV-[0-9]+(?:-[a-z]+)?)\s*\|\s*(.+?)\s*\|")


@lru_cache(maxsize=1)
def invariant_statements() -> dict[str, str]:
    """Map ``INV-0N`` -> its one-line statement, parsed from the invariants doc."""
    out: dict[str, str] = {}
    if not _DOCS.exists():
        return out
    for line in _DOCS.read_text().splitlines():
        m = _ROW.match(line)
        if m and m.group(1) not in out:
            out[m.group(1)] = m.group(2).strip()
    return out


def describe(invariants: list[str]) -> list[dict]:
    statements = invariant_statements()
    return [{"id": inv, "statement": statements.get(inv, "")} for inv in invariants]
