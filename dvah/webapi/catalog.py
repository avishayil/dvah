"""Web-facing views over the shared challenge catalog.

Builds the list and per-challenge briefing payloads. Environment resources are
summarized to their *keys only* so secret values and file contents never leak into the
briefing (the sandbox is where they matter, not the UI).
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

from ..scenarios import catalog as base
from . import invariants

_REF_CAP = 20_000  # max chars of a referenced module's source


def _module_source(module: str) -> str | None:
    """Resolve a ``dvah.*`` module to its on-disk source (read-only, size-capped)."""
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, AttributeError, ValueError):
        return None
    if not spec or not spec.origin or spec.origin in ("built-in", "frozen"):
        return None
    try:
        return Path(spec.origin).read_text()[:_REF_CAP]
    except OSError:
        return None


def _references(challenge_dir: Path) -> list[dict]:
    """Source of the ``dvah.*`` modules the editable files import — so learners can
    trace calls like ``from dvah.harness.resolver import build_envelope`` without leaving
    the UI. Read-only; deduped; non-dvah/stdlib imports skipped."""
    modules: set[str] = set()
    for f in sorted((challenge_dir / "vulnerable").glob("*.py")):
        try:
            tree = ast.parse(f.read_text())
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("dvah"):
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(a.name for a in node.names if a.name.startswith("dvah"))
    out = []
    for module in sorted(modules):
        src = _module_source(module)
        if src is not None:
            out.append({"module": module, "contents": src})
    return out


def _one_line(text: str | None) -> str:
    return " ".join((text or "").split())


def _meta(spec: dict) -> dict:
    """Learner-facing curriculum metadata (optional/defaulted for older scenarios)."""
    return {
        "order": spec.get("order", 999),
        "estimated_minutes": spec.get("estimated_minutes"),
        "teaches": _one_line(spec.get("teaches")) or None,
        "prerequisites": spec.get("prerequisites", []),
    }


def list_challenges() -> dict:
    out = []
    for spec in base.iter_scenarios():
        out.append(
            {
                "id": spec["id"],
                "title": spec.get("title", ""),
                "difficulty": spec.get("difficulty", ""),
                "invariants": spec.get("invariants", []),
                "objective": _one_line((spec.get("objective") or {}).get("exploit")),
                "blurb": _one_line((spec.get("objective") or {}).get("exploit"))[:120],
                **_meta(spec),
            }
        )
    out.sort(key=lambda c: (c["order"], c["id"]))  # beginner → advanced
    return {"challenges": out}


def _editable_files(challenge_dir: Path) -> list[dict]:
    return [
        {"path": f"vulnerable/{p.name}", "contents": p.read_text()}
        for p in sorted((challenge_dir / "vulnerable").glob("*.py"))
        if p.name != "__init__.py"
    ]


def _resource_summary(challenge_dir: Path) -> dict:
    import yaml

    path = challenge_dir / "environment" / "resources.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    # keys only — never values (files' contents / secret material stay server-side)
    summary: dict = {}
    for namespace, entries in data.items():
        summary[namespace] = list(entries.keys()) if isinstance(entries, dict) else entries
    return summary


def _yaml(challenge_dir: Path, name: str) -> dict:
    import yaml

    path = challenge_dir / "environment" / f"{name}.yaml"
    return yaml.safe_load(path.read_text()) if path.exists() else {}


def _artifacts(challenge_dir: Path) -> dict:
    """Compact, review-facing summary of a lab's file-based artifacts (skills/agents/tools).
    Values only — no secrets. Empty lists for labs that declare none."""
    from ..scenarios.loader import load_challenge

    loaded = load_challenge(challenge_dir)
    skills = [
        {
            "role": role,
            "name": m.name,
            "version": m.version,
            "description": m.description,
            "requested_permissions": [f"{c.namespace}.{c.action}" for c in m.permissions],
            "tools": list(m.tools),
        }
        for role, m in loaded.skills.items()
    ]
    agents = [
        {
            "agent_id": a.agent_id,
            "description": a.description,
            "model": a.model,
            "tools": list(a.tools),
            "skills": list(a.skills),
        }
        for a in loaded.agent_defs.values()
    ]
    tools = [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "side_effect": s.side_effect.value,
            "requires_approval": s.requires_approval,
        }
        for s in sorted(loaded.tools_catalog.values(), key=lambda s: s.id)
    ]
    resources = [
        {"id": r.id, "name": r.name, "trust": r.trust.value, "mime_type": r.mime_type}
        for r in sorted(loaded.resources.values(), key=lambda r: r.id)
    ]
    workflows = [
        {"id": w.id, "driver": w.driver.value, "steps": len(w.steps)}
        for w in sorted(loaded.workflows.values(), key=lambda w: w.id)
    ]
    prompts = [
        {"agent_id": aid, "layers": [layer.scope.value for layer in stack.layers]}
        for aid, stack in sorted(loaded.prompts.items())
    ]
    return {
        "skills": skills,
        "agents": agents,
        "tools": tools,
        "resources": resources,
        "workflows": workflows,
        "prompts": prompts,
    }


def briefing(challenge_id: str) -> dict:
    challenge_dir = base.resolve_challenge(challenge_id)
    spec = base.read_scenario(challenge_dir)
    readme = challenge_dir / "README.md"
    plans = challenge_dir / "environment" / "plans.yaml"
    import yaml

    tasks = list((yaml.safe_load(plans.read_text()) or {}).keys()) if plans.exists() else []
    objective = spec.get("objective") or {}
    return {
        "id": spec["id"],
        "title": spec.get("title", ""),
        "difficulty": spec.get("difficulty", ""),
        "invariants": invariants.describe(spec.get("invariants", [])),
        "objective_exploit": (objective.get("exploit") or "").strip(),
        "objective_fix": (objective.get("fix") or "").strip(),
        "readme_markdown": readme.read_text() if readme.exists() else "",
        "environment": {
            "users": _yaml(challenge_dir, "users"),
            "agents": _yaml(challenge_dir, "agents"),
            "resources_summary": _resource_summary(challenge_dir),
        },
        "editable_files": _editable_files(challenge_dir),
        "references": _references(challenge_dir),
        "artifacts": _artifacts(challenge_dir),
        "tasks": tasks,
        "overridden_slots": list((spec.get("overrides") or {}).keys()),
        "components": spec.get("components", []),
        **_meta(spec),
    }
