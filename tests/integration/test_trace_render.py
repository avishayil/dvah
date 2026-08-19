"""Integration: render a real run's trace and confirm violations are surfaced."""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from dvah.observability.render import render_trace, summarize_trace
from dvah.scenarios.loader import load_challenge
from dvah.security.decision import Denied

pytestmark = pytest.mark.integration

_LAB = "challenges/DVAH-001-plan-time-authorization"


def _render_to_string(trace) -> str:
    buf = io.StringIO()
    render_trace(trace, Console(file=buf, width=100, force_terminal=False))
    return buf.getvalue()


def test_vulnerable_run_flags_inv01_in_trace():
    loaded = load_challenge(_LAB, use_solution=False)
    loaded.harness.run_task(loaded.root_ctx, "DVAH-001-exploit")  # no denial: bug present
    summary = summarize_trace(loaded.trace)
    assert summary.unauthorized_executions  # the TOCTOU delete
    out = _render_to_string(loaded.trace)
    assert "INV-01" in out
    assert "task" in out  # tree root rendered


def test_solution_run_is_clean_and_denies():
    loaded = load_challenge(_LAB, use_solution=True)
    with pytest.raises(Denied):
        loaded.harness.run_task(loaded.root_ctx, "DVAH-001-exploit")
    summary = summarize_trace(loaded.trace)
    assert summary.unauthorized_executions == ()
    assert any(d["invariant"] == "INV-01" for d in summary.denials)
    out = _render_to_string(loaded.trace)
    assert "denied" in out
