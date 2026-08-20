"""Coverage for scoring/render/router_model/replay/mcp_tools branches."""

import io

import pytest
from rich.console import Console

from dvah.observability.render import render_trace
from dvah.scenarios.loader import load_challenge
from dvah.guardrails.decision import Denied


def _run(challenge, task, use_solution=False):
    lc = load_challenge(challenge, use_solution=use_solution)
    try:
        lc.harness.run_task(lc.root_ctx, task)
    except Denied:
        pass
    return lc


@pytest.mark.integration
def test_agent_exercise_not_blocked_summary():
    """Vulnerable lab via a session: the model proposes the dangerous op and it executes
    unblocked → the 'attempted, not blocked' summary branch."""
    from dvah.providers.model import AgentState
    from dvah.providers.session import ScriptedSession
    from dvah.scoring import agent_exercise
    lc = load_challenge("challenges/DVAH-001-plan-time-authorization", use_solution=False)
    session = ScriptedSession(lc.harness.cfg.model, "DVAH-001-exploit")
    try:
        lc.harness.run_session(lc.root_ctx, session, AgentState(task_id="DVAH-001-exploit"),
                               prompt="do it")
    except Exception:
        pass
    ex = agent_exercise(lc.trace, exploit_op=("files", "delete"))
    assert "not blocked" in ex.summary  # attempted (proposed) + no denial


@pytest.mark.integration
def test_deterministic_security_helper():
    from dvah.scoring import deterministic_security
    v = deterministic_security("challenges/DVAH-001-plan-time-authorization",
                               "DVAH-001-exploit", use_solution=False)
    assert v.secure is False  # vulnerable executes an unauthorized action


@pytest.mark.integration
def test_render_covers_delegate_and_unauthorized():
    console = Console(file=io.StringIO(), force_terminal=False)
    render_trace(_run("challenges/DVAH-002-privileged-child", "DVAH-002-exploit").trace, console)
    render_trace(_run("challenges/DVAH-001-plan-time-authorization", "DVAH-001-exploit").trace, console)
    out = console.file.getvalue()
    assert "task" in out


@pytest.mark.integration
def test_render_context_compiled_via_session():
    """run_session emits context.compiled → covers the compiled-event render branch."""
    from dvah.providers.session import ScriptedSession
    from dvah.providers.model import AgentState
    lc = load_challenge("challenges/DVAH-003-instruction-data-confusion")
    session = ScriptedSession(lc.harness.cfg.model, "DVAH-003-exploit")
    try:
        lc.harness.run_session(lc.root_ctx, session, AgentState(task_id="DVAH-003-exploit"),
                               prompt="triage")
    except Exception:
        pass
    console = Console(file=io.StringIO(), force_terminal=False)
    render_trace(lc.trace, console)
    assert any(e.kind == "context.compiled" for e in lc.trace.events)


@pytest.mark.unit
def test_router_model_no_live_adapter():
    from dvah.providers.router_model import _build_live
    with pytest.raises(ValueError, match="no live adapter"):
        _build_live("mistral", None)


@pytest.mark.integration
def test_replay_records_and_reproduces_denied(tmp_path):
    """Record + replay an exploit on the SOLUTION (which denies) — exercises the
    denial `pass` branches in run_and_record and replay."""
    from dvah.providers.session import ScriptedSession
    from dvah.replay import replay, run_and_record
    lc = load_challenge("challenges/DVAH-001-plan-time-authorization", use_solution=True)
    session = ScriptedSession(lc.harness.cfg.model, "DVAH-001-exploit")
    rec = tmp_path / "r.json"
    run_and_record(lc, "DVAH-001", "DVAH-001-exploit", session, rec)
    res = replay(rec, use_solution=True)
    assert res["matches"] is True


@pytest.mark.unit
def test_mcp_tools_invoke_branches(monkeypatch):
    from dvah.models.operation import Operation
    from dvah.providers.mcp_tools import MCPToolProvider

    p = MCPToolProvider()
    assert p.supports("mcp") and not p.supports("files")
    # unknown action
    assert not p.invoke(Operation(namespace="mcp", action="nope", resource="http://h/x")).ok
    # egress blocked (allowlist excludes the host)
    p.allow_hosts = {"good.example"}
    blocked = p.invoke(Operation(namespace="mcp", action="fetch", resource="http://evil.example/x"))
    assert not blocked.ok and "evil.example" in p.blocked
    # happy path + identity check via a stubbed transport (no real subprocess)
    p2 = MCPToolProvider()
    monkeypatch.setattr(p2, "_call_server", lambda req: {"ok": True, "content": "hi", "server_id": "dvah-mcp-1"})
    ok = p2.invoke(Operation(namespace="mcp", action="fetch", resource="http://any/x"))
    assert ok.ok and "any" in p2.egress
    # identity mismatch
    p3 = MCPToolProvider()
    p3.verify_identity = True
    monkeypatch.setattr(p3, "_call_server", lambda req: {"ok": True, "server_id": "WRONG"})
    assert not p3.invoke(Operation(namespace="mcp", action="fetch", resource="http://any/x")).ok
