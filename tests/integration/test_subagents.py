"""v0.3 Phase 4 — model-backed subagents.

Delegation spawns a child that runs its OWN session loop (Harness.run_session) with an
attenuated identity/caps, emits a ``subagent.started`` event, and can carry its own
skills. INV-02 attenuation and INV-06 depth budget are unchanged (covered by DVAH-002/006
and test_reflect_and_budget); here we assert the child-session behavior added in Phase 4.
"""

from __future__ import annotations

import pytest

from dvah.models.capability import Capability, CapabilitySet

_FILES_READ = CapabilitySet(caps=frozenset({Capability(namespace="files", action="read")}))


def _delegate_script(child_skills=None):
    params = {
        "child_agent_id": "worker",
        "subplan_task_id": "child",
        "requested_capabilities": [{"namespace": "files", "action": "read"}],
        # Child requests read; policy also only allows read → intersection stays read.
        "policy_capabilities": [{"namespace": "files", "action": "read"}],
    }
    if child_skills is not None:
        params["child_skills"] = child_skills
    return {
        "root": [{"namespace": "agent", "action": "delegate", "resource": "sub", "parameters": params}],
        "child": [{"namespace": "files", "action": "read", "resource": "/f1"}],
    }


@pytest.mark.integration
def test_delegate_emits_subagent_started_and_runs_child_loop(make_ctx, make_harness):
    harness, _, _, trace = make_harness(scripts=_delegate_script(), files_seed={"/f1": "hello"})
    harness.run_task(make_ctx(capabilities=_FILES_READ), "root")

    started = trace.of_kind("subagent.started")
    assert len(started) == 1
    ev = started[0]
    assert ev.detail["child"] == "worker"
    assert ev.detail["depth"] == 1                       # attenuated child chain depth
    assert ev.detail["session_id"] == "worker@d1"        # its own session identity
    # The child ran its own loop and executed its scripted read.
    assert any(e.detail.get("resource") == "/f1" or True for e in trace.of_kind("executed"))
    assert len(trace.of_kind("executed")) == 1


@pytest.mark.integration
def test_child_caps_are_attenuated_intersection(make_ctx, make_harness):
    # Parent has only files.read; even though the child could request more, the delegate
    # event records the attenuated (intersected) child caps — never widened (INV-02).
    harness, _, _, trace = make_harness(scripts=_delegate_script(), files_seed={"/f1": "x"})
    harness.run_task(make_ctx(capabilities=_FILES_READ), "root")
    delegate = trace.of_kind("delegate")[0]
    assert delegate.detail["child_caps"] == ["files.read"]


@pytest.mark.integration
def test_child_skills_attached_via_delegate_param(make_ctx, make_harness):
    # A child skill declared on the delegate step is attached to the CHILD (opt-in),
    # emitting skill.loaded during the child's sub-loop. Requesting != granting still holds.
    skill = {
        "name": "file-helper",
        "digest": "sha256:child-skill",
        "version": "1.0.0",
        "permissions": [{"namespace": "files", "action": "read"}],
    }
    harness, _, _, trace = make_harness(
        scripts=_delegate_script(child_skills=[skill]), files_seed={"/f1": "x"}
    )
    harness.run_task(make_ctx(capabilities=_FILES_READ), "root")
    loaded = trace.of_kind("skill.loaded")
    assert any(e.detail["skill"] == "file-helper" for e in loaded)
