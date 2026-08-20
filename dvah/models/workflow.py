"""Workflow — a first-class, DESCRIPTIVE model of a lab's orchestration.

The reference architecture names "workflow" as the controlled orchestration between steps
(code-driven vs LLM-driven). In DVAH that orchestration is the agent loop driven by a lab's
deterministic ``plans.yaml``. This model gives that a legible shape for docs/UI — it does **not
execute**: ``ScriptedSession``/``ContextActionModel`` over the byte-identical ``plans.yaml``
remains the executor and the CI oracle, so determinism is untouched.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class Driver(str, Enum):
    #: Deterministic, code-driven orchestration (DVAH's scripted plan / CI oracle).
    CODE = "code"
    #: LLM-driven orchestration (a live model reacting turn-by-turn).
    LLM = "llm"


class StepKind(str, Enum):
    TOOL = "tool"
    DELEGATE = "delegate"
    MODEL = "model"
    APPROVAL = "approval"


class WorkflowStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    kind: StepKind
    driver: Driver = Driver.CODE
    namespace: str = ""
    action: str = ""
    params: dict = {}
    #: Successor step ids; empty = terminal.
    next: tuple[str, ...] = ()


class Workflow(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str = ""
    description: str = ""
    driver: Driver = Driver.CODE
    steps: tuple[WorkflowStep, ...] = ()
