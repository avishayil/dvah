"""DeterministicModel — scripted plans keyed by task id.

CI-safe: no API key, no network, fully reproducible. Plans are loaded from a
challenge's ``environment/plans.yaml`` (task_id -> list of step dicts).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .model import ModelRequest, ModelResponse, PlanStep


class DeterministicModel:
    """A ModelProvider that replays scripted plans."""

    def __init__(self, scripts: dict[str, list[dict]]) -> None:
        self._scripts = scripts

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DeterministicModel":
        data = yaml.safe_load(Path(path).read_text()) or {}
        return cls(scripts=data)

    def complete(self, request: ModelRequest) -> ModelResponse:
        raw = self._scripts.get(request.task_id)
        if raw is None:
            raise KeyError(f"no scripted plan for task {request.task_id!r}")
        return ModelResponse(plan=tuple(PlanStep(**step) for step in raw))
