"""Phase 6: model identity, profiles, ModelRouter fallback, adapter tool-call mapping.

All offline — the live adapters' mapping is tested against hand-built provider responses;
no network/API calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dvah.harness.resolver import build_envelope, resolve_operation
from dvah.models.runtime import ModelIdentity, RuntimeContext
from dvah.observability.trace import TraceLog
from dvah.providers.model import AgentState, ModelResponse, PlanStep
from dvah.providers.profiles import resolve_profile
from dvah.providers.router_model import ModelRouter, build_model_session
from dvah.scenarios.loader import load_challenge

CHALLENGES = Path(__file__).resolve().parents[2] / "challenges"
DVAH_001 = CHALLENGES / "DVAH-001-plan-time-authorization"

pytestmark = pytest.mark.unit


# --- ModelIdentity + action_hash stability ---------------------------------

def test_model_identity_is_not_in_action_hash():
    """Enriching the recorded model identity must NOT change action_hash."""
    loaded = load_challenge(DVAH_001)
    ctx = loaded.root_ctx
    op = resolve_operation(PlanStep(namespace="files", action="read", resource="/tmp/file"))
    env = build_envelope(ctx, op)
    # The loader populates a rich identity; stripping it must leave the hash identical.
    stripped = env.runtime.model_copy(update={"model_identity": None})
    env2 = env.model_copy(update={"runtime": stripped})
    # And a totally different identity must also not move the hash.
    other = env.runtime.model_copy(
        update={"model_identity": ModelIdentity(provider="openai", model_id="gpt-4o")}
    )
    env3 = env.model_copy(update={"runtime": other})
    assert env.action_hash == env2.action_hash == env3.action_hash


def test_runtime_context_back_compat():
    rc = RuntimeContext(model="deterministic")
    assert rc.model_identity is None  # optional/additive


# --- profiles --------------------------------------------------------------

def test_profile_defaults_and_deterministic():
    assert resolve_profile("deterministic", env={}) == ("deterministic", None)
    assert resolve_profile("smart", env={})[0] == "anthropic"
    # unknown → safe oracle
    assert resolve_profile("nope", env={}) == ("deterministic", None)


def test_profile_env_override():
    env = {"DVAH_PROFILE_BALANCED": "openai:gpt-4o-mini"}
    assert resolve_profile("balanced", env=env) == ("openai", "gpt-4o-mini")
    assert resolve_profile("balanced", env={"DVAH_PROFILE_BALANCED": "anthropic"}) == (
        "anthropic",
        None,
    )


# --- ModelRouter fallback --------------------------------------------------

class _BoomSession:
    def next(self, messages, tools, state):
        raise RuntimeError("provider down")


class _OkSession:
    def next(self, messages, tools, state):
        from dvah.providers.model import ModelTurn
        return ModelTurn(final=True, model_identity="fallback")


def test_router_falls_through_and_emits_event():
    trace = TraceLog()
    router = ModelRouter(
        (("primary", lambda: _BoomSession()), ("backup", lambda: _OkSession())),
        trace=trace,
        task_id="t",
    )
    turn = router.next((), (), AgentState(task_id="t"))
    assert turn.model_identity == "fallback"
    fb = trace.of_kind("model.fallback")
    assert fb and fb[0].detail["from"] == "primary" and fb[0].detail["to"] == "backup"


def test_router_reraises_when_chain_exhausted():
    router = ModelRouter((("only", lambda: _BoomSession()),), task_id="t")
    with pytest.raises(RuntimeError):
        router.next((), (), AgentState(task_id="t"))


def test_build_deterministic_session_runs_like_script():
    """A router built for 'deterministic' replays the challenge's scripted plan."""
    loaded = load_challenge(DVAH_001)
    session = build_model_session(
        "deterministic",
        deterministic_provider=loaded.harness.cfg.model,
        task_id="DVAH-001-exploit",
    )
    turn = session.next((), (), AgentState(task_id="DVAH-001-exploit"))
    assert turn.tool_calls  # the scripted exploit steps
    assert turn.final


# --- live-adapter tool-call mapping (offline, mocked responses) ------------

def test_anthropic_tool_call_mapping():
    from dvah.providers.anthropic_model import map_tool_calls
    msg = {"content": [
        {"type": "text", "text": "ok"},
        {"type": "tool_use", "name": "github.repository.delete",
         "input": {"resource": "acme/app", "confirm": True}},
    ]}
    calls = map_tool_calls(msg)
    assert len(calls) == 1
    assert calls[0].namespace == "github" and calls[0].action == "repository.delete"
    assert calls[0].resource == "acme/app" and calls[0].parameters == {"confirm": True}


def test_openai_tool_call_mapping():
    from dvah.providers.openai_model import map_tool_calls
    resp = {"choices": [{"message": {"tool_calls": [
        {"function": {"name": "files.delete", "arguments": '{"resource": "/prod/db"}'}}
    ]}}]}
    calls = map_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0].namespace == "files" and calls[0].action == "delete"
    assert calls[0].resource == "/prod/db"


def test_bedrock_tool_call_mapping():
    from dvah.providers.bedrock_model import map_tool_calls
    resp = {"output": {"message": {"content": [
        {"toolUse": {"name": "cloud.instance.terminate", "input": {"resource": "i-123"}}}
    ]}}}
    calls = map_tool_calls(resp)
    assert len(calls) == 1
    assert calls[0].namespace == "cloud" and calls[0].action == "instance.terminate"
    assert calls[0].resource == "i-123"


def test_live_session_wraps_provider_as_one_turn():
    from dvah.providers.router_model import LiveSession

    class _FakeProvider:
        def complete(self, request):
            return ModelResponse(plan=(PlanStep(namespace="files", action="read",
                                                resource="/tmp/file"),))

    session = LiveSession(_FakeProvider(), task_id="t", identity="openai")
    turn = session.next((), (), AgentState(task_id="t"))
    assert turn.model_identity == "openai" and turn.final
    assert turn.tool_calls[0].namespace == "files"
    # second call terminates
    assert session.next((), (), AgentState(task_id="t")).final
