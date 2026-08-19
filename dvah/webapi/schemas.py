"""Pydantic request/response models for the web API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Marker = Literal["functional", "exploit", "invariant", "adversarial"]


# --- requests ---------------------------------------------------------------
class CreateSessionRequest(BaseModel):
    challenge_id: str = Field(max_length=128)
    mode: Literal["learn", "ctf"] = "learn"


class PutFileRequest(BaseModel):
    path: str = Field(max_length=256)
    contents: str = Field(max_length=1_000_000)


class RunRequest(BaseModel):
    markers: list[Marker] = Field(default=["functional", "exploit", "invariant"], max_length=8)
    task_id: str | None = Field(default=None, max_length=128)


class TraceRequest(BaseModel):
    task_id: str
    solution: bool = False


class MutateRequest(BaseModel):
    seed: int = 0
    count: int = 2
    reveal: bool = False


class TutorRequest(BaseModel):
    session_id: str
    question: str | None = None


class LiveRunRequest(BaseModel):
    task_id: str = Field(max_length=128)
    # A provider or profile name (anthropic|openai|bedrock|balanced|smart|…). Empty →
    # the configured tutor provider (the one a UI key was set for).
    model: str = Field(default="", max_length=64)


class SettingsUpdate(BaseModel):
    tutor_enabled: bool | None = None
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None  # stored in memory only; never echoed back
    run_mode: Literal["deterministic", "live"] | None = None


# --- responses --------------------------------------------------------------
class FileBlob(BaseModel):
    path: str
    contents: str


class InvariantStatement(BaseModel):
    id: str
    statement: str


class TestResult(BaseModel):
    name: str
    marker: str | None = None
    outcome: str  # passed | failed | error | skipped
    message: str | None = None


class InvariantStatus(BaseModel):
    id: str
    holds: bool


class InvariantBoard(BaseModel):
    holding: int
    total: int
    per: list[InvariantStatus]


class RunResponse(BaseModel):
    tests: list[TestResult]
    invariants: InvariantBoard
    stdout: str
    exit_code: int
