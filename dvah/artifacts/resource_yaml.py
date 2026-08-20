"""Load agent-facing knowledge Resources for a lab.

Two sources, in priority order:
1. A new-format ``resources/resources.yaml`` — a YAML list of Resource mappings.
2. Fallback: derive an advisory Resource view from the legacy world seed
   ``environment/resources.yaml`` (``files:``/``github:`` become read-only knowledge
   Resources). Secrets are deliberately NOT exposed as Resources — credentials stay off the
   knowledge path (INV-04).

Purely advisory: the world stores (FileStore/GithubStore) are still seeded from the same
``environment/resources.yaml`` keys elsewhere in the loader; this is an additional view.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..models.provenance import TrustLevel
from ..models.resource import Resource


def _from_world_seed(seed: dict) -> dict[str, Resource]:
    resources: dict[str, Resource] = {}
    for path, content in (seed.get("files") or {}).items():
        rid = f"file://{path}"
        resources[rid] = Resource(id=rid, name=path, uri=rid, content=str(content),
                                  mime_type="text/plain", trust=TrustLevel.UNTRUSTED_DATA)
    for repo, issues in (seed.get("github") or {}).items():
        rid = f"github://{repo}"
        resources[rid] = Resource(id=rid, name=repo, uri=rid,
                                  description="GitHub repository issues (untrusted content)",
                                  mime_type="application/json", trust=TrustLevel.UNTRUSTED_DATA)
    # Any other seeded namespace (e.g. DVAH-014's `egress` hosts) becomes an advisory
    # Resource too, so the knowledge view is uniform across labs. Secrets are NEVER
    # exposed as Resources — credentials stay off the knowledge path (INV-04).
    for namespace, entries in seed.items():
        if namespace in ("files", "github", "secrets"):
            continue
        for key, value in (entries or {}).items() if isinstance(entries, dict) else []:
            rid = f"{namespace}://{key}"
            resources[rid] = Resource(id=rid, name=key, uri=rid, content=str(value),
                                      mime_type="text/plain", trust=TrustLevel.UNTRUSTED_DATA)
    return resources


def load_resources(challenge_dir: str | Path) -> dict[str, Resource]:
    challenge_dir = Path(challenge_dir)
    new_format = challenge_dir / "resources" / "resources.yaml"
    if new_format.exists():
        raw = yaml.safe_load(new_format.read_text()) or []
        if not isinstance(raw, list):
            raise ValueError(f"{new_format}: resources.yaml must be a YAML list of Resource specs")
        out: dict[str, Resource] = {}
        for entry in raw:
            if not isinstance(entry, dict) or "id" not in entry:
                raise ValueError(f"{new_format}: each resource needs an 'id'")
            res = Resource(**entry)
            out[res.id] = res
        return out
    legacy = challenge_dir / "environment" / "resources.yaml"
    if legacy.exists():
        return _from_world_seed(yaml.safe_load(legacy.read_text()) or {})
    return {}
