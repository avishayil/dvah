"""Unit tests for the trace summarizer (pure logic behind `dvah trace`)."""

from __future__ import annotations

import pytest

from dvah.observability.render import summarize_trace
from dvah.observability.trace import TraceLog

pytestmark = pytest.mark.unit


def _authorized_execution(trace: TraceLog, h: str) -> None:
    trace.emit("policy.decision", "t", h, verdict="allow")
    trace.emit("executed", "t", h, ok=True)


def test_clean_trace_has_no_violations():
    trace = TraceLog()
    _authorized_execution(trace, "sha256:aaa")
    summary = summarize_trace(trace)
    assert summary.executed == 1
    assert summary.unauthorized_executions == ()
    assert summary.clean is True


def test_flags_execution_without_authorization():
    trace = TraceLog()
    # executed but never authorized (the TOCTOU signature)
    trace.emit("executed", "t", "sha256:bad", ok=True)
    summary = summarize_trace(trace)
    assert summary.unauthorized_executions == ("sha256:bad",)
    assert summary.clean is False


def test_collects_denials_with_invariant():
    trace = TraceLog()
    trace.emit("denied", "t", "sha256:x", invariant="INV-01")
    summary = summarize_trace(trace)
    assert summary.denials == ({"action_hash": "sha256:x", "invariant": "INV-01"},)


def test_detects_untrusted_instruction_leak():
    trace = TraceLog()
    trace.emit("context.compiled", "t", None, untrusted_instruction=True)
    assert summarize_trace(trace).untrusted_instruction is True


def test_records_delegations():
    trace = TraceLog()
    trace.emit("delegate", "t", None, child="research-agent", child_caps=["github.issue.read"])
    assert summarize_trace(trace).delegations == ("research-agent",)
