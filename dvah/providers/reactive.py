"""ContextActionModel — a model that both replays scripts and reacts to context.

A strict superset of DeterministicModel: known task ids return their scripted plan;
unknown task ids (reflection follow-ups) produce steps from any INSTRUCTION-channel
context item that carries an ``action``. That is safe only if the context compiler
kept untrusted data out of the instruction channel — which is the point of INV-06.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .model import ModelRequest, ModelResponse, PlanStep


class ContextActionModel:
    def __init__(self, scripts: dict[str, list[dict]]) -> None:
        self._scripts = scripts

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ContextActionModel":
        data = yaml.safe_load(Path(path).read_text()) or {}
        return cls(scripts=data)

    def complete(self, request: ModelRequest) -> ModelResponse:
        scripted = self._scripts.get(request.task_id)
        if scripted is not None:
            return ModelResponse(plan=tuple(PlanStep(**step) for step in scripted))

        # React: follow any action embedded in an INSTRUCTION-channel item. This is
        # only reached for data that the compiler placed in the instruction channel —
        # a correct compiler keeps untrusted data out of it (INV-06).
        steps: list[PlanStep] = []
        for item in request.context:
            if item.get("channel") != "instruction":
                continue
            for action in _find_actions(item.get("content", {})):
                steps.append(PlanStep(**action))
        return ModelResponse(plan=tuple(steps))


def _find_actions(value) -> list[dict]:
    """Recursively collect dicts stored under an ``action`` key."""
    found: list[dict] = []
    if isinstance(value, dict):
        candidate = value.get("action")
        if isinstance(candidate, dict) and "namespace" in candidate:
            found.append(candidate)
        for v in value.values():
            found.extend(_find_actions(v))
    elif isinstance(value, (list, tuple)):
        for v in value:
            found.extend(_find_actions(v))
    return found
