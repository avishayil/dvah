"""Full-stack e2e: drive the Harness with HttpToolProvider against live services."""

import pytest

from dvah.harness.config import HarnessConfig
from dvah.harness.context import RunContext
from dvah.harness.executor import BuiltinExecutor
from dvah.harness.loop import Harness
from dvah.models.capability import Capability, CapabilitySet
from dvah.models.envelope import Intent
from dvah.models.identity import Actor, DelegationChain, Principal
from dvah.models.runtime import Constraints, RuntimeContext
from dvah.observability.trace import TraceLog
from dvah.providers.deterministic import DeterministicModel
from dvah.providers.http_tools import HttpToolProvider
from dvah.security.approvals import BuiltinApprovalService
from dvah.security.capabilities import BuiltinCapabilityResolver
from dvah.security.policy import BuiltinPolicy
from dvah.security.provenance import BuiltinProvenanceTracker
from dvah.security.secrets import BuiltinSecretBroker

pytestmark = pytest.mark.e2e


def _make_harness(base_urls) -> Harness:
    cfg = HarnessConfig(
        model=DeterministicModel(
            {"read-issue": [{"namespace": "github", "action": "issue.read", "resource": "repo/x/y"}]}
        ),
        policy=BuiltinPolicy(),
        approvals=BuiltinApprovalService(),
        capabilities=BuiltinCapabilityResolver(),
        provenance=BuiltinProvenanceTracker(),
        secrets=BuiltinSecretBroker(),
        tools=HttpToolProvider(base_urls=base_urls),
        executor=BuiltinExecutor(),
        trace=TraceLog(),
    )
    return Harness(cfg)


def _root_ctx() -> RunContext:
    return RunContext(
        principal=Principal(user="alice", tenant="acme"),
        actor=Actor(agent_id="agent", instance_id="agent-inst"),
        delegation=DelegationChain(root_principal="alice", chain=("agent",), depth=0),
        intent=Intent(task_id="read-issue", purpose="read"),
        capabilities=CapabilitySet(caps=frozenset({Capability(namespace="github", action="issue.read")})),
        constraints=Constraints(),
        runtime=RuntimeContext(model="deterministic"),
    )


def test_harness_reads_from_live_github(services, reset_services):
    reset_services({"github": {"github": {"repo/x/y": {"issues": [{"id": 7, "title": "live"}]}}}})
    harness = _make_harness(services)
    results = harness.run_task(_root_ctx(), "read-issue")
    assert results[0].ok
    assert results[0].output["issues"][0]["id"] == 7
