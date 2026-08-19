import pytest

from dvah.observability.trace import TraceLog

pytestmark = pytest.mark.unit


def test_emit_and_events():
    log = TraceLog()
    log.emit("executed", "t", "sha256:a", ok=True)
    assert len(log.events) == 1
    assert log.events[0].kind == "executed"
    assert log.events[0].detail == {"ok": True}


def test_of_kind_filters():
    log = TraceLog()
    log.emit("executed", "t", "h1")
    log.emit("denied", "t", "h2")
    assert len(log.of_kind("executed")) == 1


def test_authorized_hashes_includes_allow_and_needs_approval_only():
    log = TraceLog()
    log.emit("policy.decision", "t", "h_allow", verdict="allow")
    log.emit("policy.decision", "t", "h_appr", verdict="needs_approval")
    log.emit("policy.decision", "t", "h_deny", verdict="deny")
    assert log.authorized_hashes() == {"h_allow", "h_appr"}


def test_executed_hashes():
    log = TraceLog()
    log.emit("executed", "t", "h1")
    log.emit("executed", "t", "h2")
    log.emit("denied", "t", "h3")
    assert log.executed_hashes() == ["h1", "h2"]


def test_single_authorization_licenses_single_execution():
    """INV-01 occurrence regression (review #1): one authorization must not license
    executing the same resolved action twice. The old set-membership check passed this
    (the hash was 'authorized'); occurrence-level pairing flags the replayed execution."""
    log = TraceLog()
    log.emit("policy.decision", "t", "sha256:H", action_id="act-0", verdict="allow")
    log.emit("executed", "t", "sha256:H", action_id="act-0")
    log.emit("executed", "t", "sha256:H", action_id="act-0")  # replay, no fresh decision
    # hash is in the authorized set, so the old check would have returned []:
    assert "sha256:H" in log.authorized_hashes()
    # occurrence pairing consumes the one authorization and flags the second execution:
    assert log.unauthorized_executions() == ["sha256:H"]


def test_two_distinct_occurrences_each_need_their_own_authorization():
    """Two genuinely separate executions (distinct action_ids) are fine when each has its
    own allowing decision — the correct broker ticks the occurrence id per step."""
    log = TraceLog()
    for aid in ("act-0", "act-1"):
        log.emit("policy.decision", "t", "sha256:H", action_id=aid, verdict="allow")
        log.emit("executed", "t", "sha256:H", action_id=aid)
    assert log.unauthorized_executions() == []
