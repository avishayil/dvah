"""Record & replay of agent sessions.

A live (or deterministic) run can be RECORDED — the normalized ``ModelTurn``s plus the
resulting security trace and verdict are serialized to JSON. ``replay`` re-runs the
harness feeding those recorded turns back through a ``ReplaySession`` (which yields the
recorded tool calls in order and makes NO model calls), reproducing the same security
verdict deterministically. This gives realism + repeatability without paying for — or
depending on the nondeterminism of — another model call.
"""

from __future__ import annotations

import json
from pathlib import Path

from .providers.model import AgentState, Message, ModelTurn
from .scoring import security_verdict


class RecordingSession:
    """Wraps any ``ModelSession`` and records each ``ModelTurn`` it returns."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.turns: list[ModelTurn] = []

    def next(self, messages, tools, state):
        turn = self._inner.next(messages, tools, state)
        self.turns.append(turn)
        return turn


class ReplaySession:
    """A ``ModelSession`` that yields pre-recorded turns in order — no model calls."""

    def __init__(self, turns: list[ModelTurn]) -> None:
        self._turns = list(turns)
        self._i = 0

    def next(self, messages: tuple[Message, ...], tools: tuple[str, ...], state: AgentState) -> ModelTurn:
        if self._i >= len(self._turns):
            return ModelTurn(final=True)
        turn = self._turns[self._i]
        self._i += 1
        return turn


def _trace_events(trace) -> list[dict]:
    return [
        {
            "kind": e.kind,
            "task_id": e.task_id,
            "action_hash": e.action_hash,
            "action_id": e.action_id,
            "detail": e.detail,
        }
        for e in trace.events
    ]


def run_and_record(loaded, challenge_id: str, task_id: str, session, path: str | Path) -> dict:
    """Run ``session`` through the loaded harness, recording turns + trace + verdict to ``path``."""
    rec = RecordingSession(session)
    try:
        loaded.harness.run_session(
            loaded.root_ctx, rec, AgentState(task_id=task_id), prompt=loaded.task_prompt(task_id)
        )
    except Exception:  # a denial legitimately halts the run; the trace still records it
        pass
    verdict = security_verdict(loaded.trace)
    data = {
        "challenge_id": challenge_id,
        "task_id": task_id,
        "turns": [t.model_dump() for t in rec.turns],
        "trace": _trace_events(loaded.trace),
        "security": {"secure": verdict.secure, "unauthorized": list(verdict.unauthorized)},
    }
    Path(path).write_text(json.dumps(data, indent=2))
    return data


def load_recording(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def replay(path: str | Path, use_solution: bool = False) -> dict:
    """Reload the recorded challenge and replay its turns — no model calls. Returns the
    reproduced verdict and whether it matches what was recorded."""
    from .scenarios.catalog import resolve_challenge
    from .scenarios.loader import load_challenge

    data = load_recording(path)
    loaded = load_challenge(resolve_challenge(data["challenge_id"]), use_solution=use_solution)
    turns = [ModelTurn(**t) for t in data["turns"]]
    session = ReplaySession(turns)
    try:
        loaded.harness.run_session(
            loaded.root_ctx,
            session,
            AgentState(task_id=data["task_id"]),
            prompt=loaded.task_prompt(data["task_id"]),
        )
    except Exception:
        pass
    verdict = security_verdict(loaded.trace)
    reproduced = {"secure": verdict.secure, "unauthorized": list(verdict.unauthorized)}
    return {
        "challenge_id": data["challenge_id"],
        "task_id": data["task_id"],
        "reproduced": reproduced,
        "recorded": data.get("security"),
        "matches": reproduced == data.get("security"),
        "trace": _trace_events(loaded.trace),
    }
