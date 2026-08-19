"""Model provider protocol and its request/response types.

The harness is model-agnostic: everything downstream operates on ActionEnvelopes, not
on model output. A provider only turns a task into a proposed plan.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class PlanStep(BaseModel):
    """One proposed step. A plan has NO authority until resolved into an envelope."""

    model_config = ConfigDict(frozen=True)

    namespace: str
    action: str
    resource: str
    parameters: dict = {}


class ModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    task_id: str
    prompt: str = ""
    context: tuple[dict, ...] = ()


class ModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan: tuple[PlanStep, ...]


@runtime_checkable
class ModelProvider(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...


# --- Stateful agent-loop abstraction (v0.3) --------------------------------
#
# The one-shot ``ModelProvider.complete → full plan`` seam above is kept for
# back-compat and as the deterministic CI oracle. On top of it we model a real
# agent as a *session*: the harness feeds messages + available tools, the model
# returns one ``ModelTurn`` (proposed tool calls or a final answer), the harness
# resolves + gates + executes each call, feeds the observation back, and asks for
# the next turn. The model only ever *proposes* — authority is still conferred by
# the harness in ``ActionBroker.run_step``.


class ToolCall(BaseModel):
    """A model-proposed action. No authority until the harness resolves it."""

    model_config = ConfigDict(frozen=True)

    namespace: str
    action: str
    resource: str = ""
    parameters: dict = {}

    def to_plan_step(self) -> "PlanStep":
        return PlanStep(
            namespace=self.namespace,
            action=self.action,
            resource=self.resource,
            parameters=self.parameters,
        )


class Usage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = 0
    output_tokens: int = 0


class Message(BaseModel):
    """One entry in the running conversation fed to a session."""

    model_config = ConfigDict(frozen=True)

    role: str = "user"  # "user" | "assistant" | "tool"
    content: str = ""
    context: tuple[dict, ...] = ()  # compiled model context (data/instruction items)


class AgentState(BaseModel):
    """Loop-carried state a session may need (e.g. the current task)."""

    model_config = ConfigDict(frozen=True)

    task_id: str
    turns: int = 0


class ModelTurn(BaseModel):
    """One assistant turn: proposed tool calls and/or a final answer."""

    model_config = ConfigDict(frozen=True)

    text: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    final: bool = False
    usage: Usage | None = None
    model_identity: str | None = None


@runtime_checkable
class ModelSession(Protocol):
    def next(
        self,
        messages: tuple[Message, ...],
        tools: tuple[str, ...],
        state: AgentState,
    ) -> ModelTurn: ...
