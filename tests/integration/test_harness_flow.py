"""Integration tests: full plan execution through the correct (Builtin*) harness."""

import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.security.decision import Denied

pytestmark = pytest.mark.integration


def _caps(*pairs):
    return CapabilitySet(caps=frozenset(Capability(namespace=n, action=a) for n, a in pairs))


def test_happy_path_mutates_store(make_harness, make_ctx):
    scripts = {"t": [{"namespace": "files", "action": "rename", "resource": "/a",
                      "parameters": {"dest": "/b"}}]}
    harness, files, _, _ = make_harness(scripts, files_seed={"/a": "x"})
    ctx = make_ctx(capabilities=_caps(("files", "rename")))
    results = harness.run_task(ctx, "t")
    assert results[0].ok
    assert files.exists("/b") and not files.exists("/a")


def test_unauthorized_action_denied_and_store_unchanged(make_harness, make_ctx):
    scripts = {"t": [{"namespace": "files", "action": "rename", "resource": "/a",
                      "parameters": {"dest": "/b"}}]}
    harness, files, _, _ = make_harness(scripts, files_seed={"/a": "x"})
    ctx = make_ctx(capabilities=_caps())  # no capabilities
    with pytest.raises(Denied) as e:
        harness.run_task(ctx, "t")
    assert e.value.decision.invariant == "INV-01"
    assert files.exists("/a")


def test_approval_required_action_executes(make_harness, make_ctx):
    scripts = {"t": [{"namespace": "files", "action": "delete", "resource": "/secret"}]}
    harness, files, _, trace = make_harness(scripts, files_seed={"/secret": "x"})
    ctx = make_ctx(capabilities=_caps(("files", "delete")))
    results = harness.run_task(ctx, "t")
    assert results[0].ok
    assert not files.exists("/secret")
    verdicts = {e.detail.get("verdict") for e in trace.of_kind("policy.decision")}
    assert "needs_approval" in verdicts


def test_delegation_attenuates_and_denies_out_of_scope(make_harness, make_ctx):
    scripts = {
        "root": [{"namespace": "agent", "action": "delegate", "resource": "sub",
                  "parameters": {
                      "child_agent_id": "kid",
                      "requested_capabilities": [{"namespace": "github", "action": "issue.read"},
                                                 {"namespace": "github", "action": "issue.comment"}],
                      "policy_capabilities": [{"namespace": "github", "action": "issue.read"},
                                              {"namespace": "github", "action": "issue.comment"}],
                      "subplan_task_id": "child_write"}}],
        "child_write": [{"namespace": "github", "action": "issue.comment", "resource": "repo/a",
                         "parameters": {"issue": 1, "body": "x"}}],
    }
    harness, _, _, _ = make_harness(scripts, github_seed={"repo/a": {"issues": []}})
    # parent only has read; child requests comment -> attenuated away -> denied
    ctx = make_ctx(capabilities=_caps(("github", "issue.read")))
    with pytest.raises(Denied) as e:
        harness.run_task(ctx, "root")
    assert e.value.decision.invariant == "INV-01"


def test_delegated_child_within_scope_succeeds(make_harness, make_ctx):
    scripts = {
        "root": [{"namespace": "agent", "action": "delegate", "resource": "sub",
                  "parameters": {
                      "child_agent_id": "kid",
                      "requested_capabilities": [{"namespace": "github", "action": "issue.read"}],
                      "policy_capabilities": [{"namespace": "github", "action": "issue.read"}],
                      "subplan_task_id": "child_read"}}],
        "child_read": [{"namespace": "github", "action": "issue.read", "resource": "repo/a"}],
    }
    harness, _, _, _ = make_harness(scripts, github_seed={"repo/a": {"issues": [{"id": 7}]}})
    ctx = make_ctx(capabilities=_caps(("github", "issue.read")))
    results = harness.run_task(ctx, "root")
    assert results[0].output["issues"][0]["id"] == 7


def test_credential_is_out_of_band_and_authorized_equals_executed(make_harness, make_ctx):
    """Phase 5 (review #9): the credential reaches the tool as a separate argument, never
    in Operation.parameters, so the executed operation is byte-for-byte the authorized one
    (the ``executed`` trace hash equals the ``policy.decision`` hash for that occurrence)."""
    from dvah.providers.model import PlanStep
    from dvah.providers.tools import ToolResult

    seen = {}

    class RecordingProvider:
        def supports(self, namespace):
            return True

        def invoke(self, operation, credential=None):
            seen["operation"] = operation
            seen["credential"] = credential
            return ToolResult(ok=True, output={}, source=f"{operation.namespace}:{operation.resource}")

    harness, _, _, trace = make_harness(
        {"t": []}, credentials={"github": "ghp_secret"},
        slots={"tools": RecordingProvider()},
    )
    ctx = make_ctx(capabilities=_caps(("github", "issue.comment")))
    outcome = harness.broker.run_step(
        ctx, PlanStep(namespace="github", action="issue.comment", resource="repo/a",
                      parameters={"issue": 1, "body": "hi"})
    )
    assert outcome.result.ok
    # credential arrived out-of-band; operation carries no credential material
    assert seen["credential"] == "ghp_secret"
    assert "_credential" not in seen["operation"].parameters
    # authorized == executed for the same occurrence
    decision = trace.of_kind("policy.decision")[-1]
    executed = trace.of_kind("executed")[-1]
    assert executed.action_hash == decision.action_hash
    assert executed.action_id == decision.action_id


def test_provenance_recorded_after_tool_call(make_harness, make_ctx):
    from dvah.providers.model import PlanStep

    scripts = {"t": [{"namespace": "files", "action": "read", "resource": "/a"}]}
    harness, _, _, _ = make_harness(scripts, files_seed={"/a": "data"})
    ctx = make_ctx(capabilities=_caps(("files", "read")))
    outcome = harness.broker.run_step(
        ctx, PlanStep(namespace="files", action="read", resource="/a")
    )
    assert outcome.result.ok
    assert len(outcome.ctx.provenance.data_sources) == 1
    assert outcome.ctx.provenance.data_sources[0].source == "files:/a"
