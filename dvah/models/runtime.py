"""Runtime context and constraints — USING WHAT / UNDER WHAT LIMITS.

Captures which model, skill, and MCP server produced an action, plus the resource
limits (delegation depth, action budget) that bound its execution.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SkillRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    digest: str


class MCPServerRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    digest: str


class Constraints(BaseModel):
    """Runtime limits inherited down a delegation chain."""

    model_config = ConfigDict(frozen=True)

    network_profile: str = "restricted"
    delegation_depth: int = 2
    max_actions: int = 20


class ModelIdentity(BaseModel):
    """WHICH model proposed an action — recorded for the trace and the fallback lesson.

    ``provider`` is the coarse label that also feeds ``RuntimeContext.model`` (and is
    therefore the ONLY model field that reaches ``action_hash`` — a richer identity must
    not change the semantic hash). The rest is observability: model id/version, sampling,
    the tool-calling mode, the adapter version, a per-session id, and the configured
    fallback chain (so a silent fallback to a differently-behaving model is visible).
    """

    model_config = ConfigDict(frozen=True)

    provider: str
    model_id: str | None = None
    version: str | None = None
    temperature: float | None = None
    tool_mode: str | None = None
    adapter_version: str | None = None
    session_id: str | None = None
    fallback_chain: tuple[str, ...] = ()


class RuntimeContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Coarse provider label. Kept as the hash input (see ModelIdentity) so enriching the
    # recorded identity below never perturbs action_hash.
    model: str
    # Richer, observability-only identity (never hashed). Optional for back-compat.
    model_identity: ModelIdentity | None = None
    skill: SkillRef | None = None
    mcp_server: MCPServerRef | None = None
