"""Load a lab's deterministic ``plans.yaml`` into descriptive Workflow objects.

Advisory only: this produces a legible ``Workflow`` per task for docs/UI. It does NOT execute —
``ContextActionModel``/``ScriptedSession`` over the byte-identical ``plans.yaml`` remains the
executor and CI oracle. One ``Workflow`` per ``task_id`` (the plan keys).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..models.workflow import Driver, StepKind, Workflow, WorkflowStep


def _step_kind(namespace: str, action: str) -> StepKind:
    if namespace == "agent":
        return StepKind.MODEL if action == "reflect" else StepKind.DELEGATE
    return StepKind.TOOL


def _resolve_plans_path(challenge_dir: Path) -> Path | None:
    for candidate in (challenge_dir / "workflows" / "plans.yaml",
                      challenge_dir / "environment" / "plans.yaml"):
        if candidate.exists():
            return candidate
    return None


def load_workflows(challenge_dir: str | Path) -> dict[str, Workflow]:
    """Return ``{task_id: Workflow}`` for every scripted plan (empty if none)."""
    challenge_dir = Path(challenge_dir)
    path = _resolve_plans_path(challenge_dir)
    if path is None:
        return {}
    plans = yaml.safe_load(path.read_text()) or {}
    workflows: dict[str, Workflow] = {}
    for task_id, raw_steps in plans.items():
        steps = []
        for i, raw in enumerate(raw_steps or []):
            ns, action = raw.get("namespace", ""), raw.get("action", "")
            nxt = (f"{task_id}-{i + 1}",) if i + 1 < len(raw_steps) else ()
            steps.append(WorkflowStep(
                id=f"{task_id}-{i}", kind=_step_kind(ns, action), driver=Driver.CODE,
                namespace=ns, action=action, params=raw.get("parameters", {}) or {}, next=nxt,
            ))
        workflows[task_id] = Workflow(id=task_id, name=task_id, driver=Driver.CODE,
                                      steps=tuple(steps))
    return workflows
