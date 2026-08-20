"""Tiered hints, guided walkthrough, and the gated solution diff.

Hint tiers and walkthrough steps come from a challenge's ``walkthrough.yaml`` (authored
separately). If that file is absent, a minimal single-tier fallback keeps the endpoints
working. The solution diff is computed server-side with ``difflib`` and only served by
the explicit ``/solution`` route.
"""

from __future__ import annotations

import difflib
from pathlib import Path

import yaml

from ..scenarios import catalog


def _walkthrough(challenge_dir: Path) -> dict:
    path = challenge_dir / "walkthrough.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def hint_index(challenge_id: str) -> dict:
    challenge_dir = catalog.resolve_challenge(challenge_id)
    spec = catalog.read_scenario(challenge_dir)
    data = _walkthrough(challenge_dir)
    tiers = data.get("tiers")
    if not tiers:  # fallback so the endpoint works before content is authored
        tiers = [{"level": "concept", "text": (spec.get("objective") or {}).get("fix", "")}]
    invariant = data.get("invariant") or (spec.get("invariants") or [None])[0]
    return {
        "invariant": invariant,
        "count": len(tiers),
        "tiers": [{"level": t.get("level", "hint"), "revealed": False} for t in tiers],
    }


def hint_tier(challenge_id: str, index: int) -> dict:
    challenge_dir = catalog.resolve_challenge(challenge_id)
    data = _walkthrough(challenge_dir)
    tiers = data.get("tiers") or hint_index(challenge_id)["tiers"]
    if index < 0 or index >= len(tiers):
        raise IndexError(index)
    tier = tiers[index]
    return {"level": tier.get("level", "hint"), "text": tier.get("text", "")}


def walkthrough_steps(challenge_id: str) -> list[str]:
    challenge_dir = catalog.resolve_challenge(challenge_id)
    return list(_walkthrough(challenge_dir).get("steps", []))


def solution(challenge_id: str) -> dict:
    """Reveal solution files + a unified diff vs the original vulnerable code."""
    challenge_dir = catalog.resolve_challenge(challenge_id)
    vuln = challenge_dir / "guardrails" / "vulnerable"
    sol = challenge_dir / "guardrails" / "solution"
    files: list[dict] = []
    diff_parts: list[str] = []
    for sol_file in sorted(sol.glob("*.py")):
        if sol_file.name == "__init__.py":
            continue
        files.append({"path": f"guardrails/solution/{sol_file.name}", "contents": sol_file.read_text()})
        vuln_file = vuln / sol_file.name
        before = vuln_file.read_text().splitlines(keepends=True) if vuln_file.exists() else []
        after = sol_file.read_text().splitlines(keepends=True)
        diff_parts.extend(
            difflib.unified_diff(
                before, after,
                fromfile=f"guardrails/vulnerable/{sol_file.name}", tofile=f"guardrails/solution/{sol_file.name}",
            )
        )
    return {"files": files, "diff": "".join(diff_parts)}
