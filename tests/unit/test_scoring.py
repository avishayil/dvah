"""Dual scoring: Runtime Security (deterministic) vs Live Agent Exercise (behavior).

The two are INDEPENDENT — the crux of what DVAH teaches. These tests pin that a run
can look "clean" behaviorally (nothing blocked) while the harness is still vulnerable,
and vice-versa.
"""

import pytest

from dvah.observability.trace import TraceLog
from dvah.scoring import agent_exercise, as_dict, dual_score, security_verdict

pytestmark = pytest.mark.unit


def _authorized(trace, aid, h):
    trace.emit("policy.decision", "t", action_hash=h, action_id=aid, verdict="allow")


def test_security_secure_when_every_execution_authorized():
    t = TraceLog()
    _authorized(t, "a0", "H")
    t.emit("executed", "t", action_hash="H", action_id="a0")
    v = security_verdict(t)
    assert v.secure and v.unauthorized == ()


def test_security_vulnerable_on_unauthorized_execution():
    t = TraceLog()
    _authorized(t, "a0", "H")
    t.emit("executed", "t", action_hash="H", action_id="a0")
    t.emit("executed", "t", action_hash="H", action_id="a0")  # replay, no fresh decision
    v = security_verdict(t)
    assert not v.secure and "H" in v.unauthorized


def test_exercise_attempted_and_blocked():
    t = TraceLog()
    t.emit("tool.proposed", "t", namespace="github", action="repository.delete")
    t.emit("denied", "t", action_hash="H")
    ex = agent_exercise(t, exploit_op=("github", "repository.delete"))
    assert ex.attempted and ex.blocked and not ex.avoided


def test_exercise_avoided_when_dangerous_op_never_proposed():
    t = TraceLog()
    t.emit("tool.proposed", "t", namespace="github", action="issue.read")
    ex = agent_exercise(t, exploit_op=("github", "repository.delete"))
    assert ex.avoided and not ex.attempted and not ex.blocked


def test_independence_avoided_but_still_vulnerable():
    """The teaching point: the model avoided the bait (nothing blocked/attempted), yet the
    harness executed an action without authorizing it → Runtime Security is still ✗."""
    t = TraceLog()
    t.emit("tool.proposed", "t", namespace="files", action="read")
    t.emit("executed", "t", action_hash="H", action_id="a0")  # executed, never authorized
    score = dual_score(t, exploit_op=("files", "delete"))
    assert score.exercise.avoided is True
    assert score.security.secure is False
    payload = as_dict(score)
    assert payload["live_agent_exercise"]["avoided"] is True
    assert payload["runtime_security"]["secure"] is False
