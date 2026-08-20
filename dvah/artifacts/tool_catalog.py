"""Load tool specifications from YAML into a ``{id: ToolSpec}`` catalog.

The built-in catalog is the provider-shared source of truth: one spec per
``namespace.action`` the tool providers implement, kept in ``dvah/tools/catalog/*.yaml``.
A lab may ``overlay`` a per-lab ``environment/tools.yaml`` to advertise or refine a subset.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from ..models.tool_spec import ToolSpec

CATALOG_DIR = Path(__file__).resolve().parent.parent / "tools" / "catalog"


def load_catalog_file(path: str | Path) -> dict[str, ToolSpec]:
    """Parse a YAML list of tool-spec mappings into ``{id: ToolSpec}``."""
    path = Path(path)
    raw = yaml.safe_load(path.read_text()) or []
    if not isinstance(raw, list):
        raise ValueError(f"{path}: tool catalog file must be a YAML list of tool specs")
    catalog: dict[str, ToolSpec] = {}
    for entry in raw:
        if not isinstance(entry, dict) or "namespace" not in entry or "action" not in entry:
            raise ValueError(f"{path}: each tool spec needs 'namespace' and 'action'")
        spec = ToolSpec(**entry)
        catalog[spec.id] = spec
    return catalog


@lru_cache(maxsize=1)
def builtin_catalog() -> dict[str, ToolSpec]:
    """Merge every ``dvah/tools/catalog/*.yaml`` into one catalog (cached)."""
    catalog: dict[str, ToolSpec] = {}
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        catalog.update(load_catalog_file(path))
    return catalog


def overlay(base: dict[str, ToolSpec], extra: dict[str, ToolSpec]) -> dict[str, ToolSpec]:
    """Return a new catalog with ``extra`` specs added/overriding ``base`` (immutable)."""
    return {**base, **extra}
