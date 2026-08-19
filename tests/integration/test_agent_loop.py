"""Integration tests for the v0.3 agent loop (Harness.run_session).

The loop must reproduce the old fixed-plan behavior under the deterministic session
(the whole plan runs through the executor slot in one turn, so the DVAH-001-style
executor break still applies) and must respect the action budget for a session that
keeps proposing calls.
"""

import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.models.runtime import Constraints
from dvah.providers.model import AgentState, ModelTurn, ToolCall

pytestmark = pytest.mark.integration


def _caps(*pairs):
    return CapabilitySet(caps=frozenset(Capability(namespace=n, action=a) for n, a in pairs))


def test_run_session_runs_whole_plan_through_executor(make_harness, make_ctx):
    """run_task now drives a ModelSession; a multi-step plan still executes end to end
    via the executor slot (one execute_plan call), mutating the store."""
    scripts = {"t": [
        {"namespace": "files", "action": "rename", "resource": "/a", "parameters": {"dest": "/b"}},
        {"namespace": "files", "action": "delete", "resource": "/b"},
    ]}
    harness, files, _, trace = make_harness(scripts, files_seed={"/a": "x"})
    ctx = make_ctx(capabilities=_caps(("files", "rename"), ("files", "delete")))

    results = harness.run_task(ctx, "t")

    assert [r.ok for r in results] == [True, True]
    assert not files.exists("/a") and not files.exists("/b")
    # Both actions reached the gate + executed as distinct occurrences.
    assert len(trace.of_kind("executed")) == 2


def test_run_session_respects_max_actions(make_harness, make_ctx):
    """A session that never finalizes is bounded by Constraints.max_actions."""

    class _EndlessReadSession:
        def next(self, messages, tools, state: AgentState) -> ModelTurn:
            return ModelTurn(
                tool_calls=(ToolCall(namespace="files", action="read", resource="/a"),),
                final=False,
            )

    harness, _, _, trace = make_harness({}, files_seed={"/a": "x"})
    ctx = make_ctx(
        capabilities=_caps(("files", "read")),
        constraints=Constraints(max_actions=3),
    )

    results = harness.run_session(ctx, _EndlessReadSession())

    # The loop stops at the budget instead of spinning forever.
    assert len(results) == 3
    assert len(trace.of_kind("executed")) == 3
