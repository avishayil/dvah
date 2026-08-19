"""Deterministic ModelSession — the CI oracle for the agent loop.

Adapts any one-shot ``ModelProvider`` (e.g. ``ContextActionModel`` /
``DeterministicModel``, loaded from a challenge's ``plans.yaml``) to the stateful
``ModelSession`` interface. It replays the provider's scripted plan as a SINGLE
turn's tool calls, then a final turn.

Emitting the whole plan in one turn is deliberate: the executor slot is a security
boundary (DVAH-001's vulnerable executor authorizes once then executes the *rest* of
the plan), so the full plan must reach ``executor.execute_plan`` in one call for that
lab to break. Live sessions (later phases) instead emit tool calls turn-by-turn and
react to observations — but the per-call gate is identical.
"""

from __future__ import annotations

from .model import (
    AgentState,
    Message,
    ModelProvider,
    ModelRequest,
    ModelTurn,
    ToolCall,
)


class ScriptedSession:
    """A ``ModelSession`` that replays a ``ModelProvider``'s scripted plan."""

    def __init__(
        self,
        provider: ModelProvider,
        task_id: str,
        context: tuple[dict, ...] = (),
    ) -> None:
        self._provider = provider
        self._task_id = task_id
        self._context = context
        self._emitted = False

    def next(
        self,
        messages: tuple[Message, ...],
        tools: tuple[str, ...],
        state: AgentState,
    ) -> ModelTurn:
        if self._emitted:
            return ModelTurn(final=True)
        self._emitted = True
        response = self._provider.complete(
            ModelRequest(task_id=self._task_id, context=self._context)
        )
        calls = tuple(
            ToolCall(
                namespace=step.namespace,
                action=step.action,
                resource=step.resource,
                parameters=step.parameters,
            )
            for step in response.plan
        )
        return ModelTurn(tool_calls=calls, final=True, model_identity="deterministic")
