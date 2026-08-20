"""Shared builder fixtures for unit and integration tests.

These construct a fully-correct harness (all Builtin* parts) so tests do not need the
``--challenge`` machinery from the repo-root conftest.
"""

from __future__ import annotations

import pytest

from dvah.harness.config import HarnessConfig
from dvah.harness.context import RunContext
from dvah.harness.executor import BuiltinExecutor
from dvah.harness.loop import Harness
from dvah.harness.resolver import build_envelope
from dvah.models.capability import CapabilitySet
from dvah.models.envelope import Intent
from dvah.models.identity import Actor, DelegationChain, Principal
from dvah.models.operation import Operation
from dvah.models.runtime import Constraints, RuntimeContext
from dvah.observability.trace import TraceLog
from dvah.providers.deterministic import DeterministicModel
from dvah.providers.native_tools import NativeToolProvider
from dvah.guardrails.approvals import BuiltinApprovalService
from dvah.guardrails.capabilities import BuiltinCapabilityResolver
from dvah.guardrails.policy import BuiltinPolicy
from dvah.guardrails.provenance import BuiltinProvenanceTracker
from dvah.guardrails.secrets import BuiltinSecretBroker
from dvah.services.world_state import FileStore, GithubStore

CLOCK = "2026-01-01T00:00:00Z"


@pytest.fixture
def make_ctx():
    def _make(capabilities=None, constraints=None, agent_id="root-agent",
              task_id="task-test", user="alice", tenant="acme"):
        return RunContext(
            principal=Principal(user=user, tenant=tenant),
            actor=Actor(agent_id=agent_id, instance_id=f"{agent_id}-inst"),
            delegation=DelegationChain(root_principal=user, chain=(agent_id,), depth=0),
            intent=Intent(task_id=task_id, purpose="test"),
            capabilities=capabilities or CapabilitySet(),
            constraints=constraints or Constraints(),
            runtime=RuntimeContext(model="deterministic"),
        )
    return _make


@pytest.fixture
def make_envelope(make_ctx):
    def _make(operation=None, ctx=None, capabilities=None):
        ctx = ctx or make_ctx(capabilities=capabilities)
        op = operation or Operation(namespace="files", action="read", resource="/tmp/x")
        return build_envelope(ctx, op)
    return _make


@pytest.fixture
def make_harness():
    def _make(scripts, files_seed=None, github_seed=None, credentials=None, slots=None):
        files = FileStore(seed=files_seed or {})
        github = GithubStore(seed=github_seed or {})
        trace = TraceLog()
        cfg_slots = dict(
            model=DeterministicModel(scripts=scripts),
            policy=BuiltinPolicy(),
            approvals=BuiltinApprovalService(),
            capabilities=BuiltinCapabilityResolver(),
            provenance=BuiltinProvenanceTracker(),
            secrets=BuiltinSecretBroker(credentials=credentials or {}),
            tools=NativeToolProvider(files=files, github=github),
            executor=BuiltinExecutor(),
            trace=trace,
        )
        if slots:
            cfg_slots.update(slots)
        return Harness(HarnessConfig(**cfg_slots)), files, github, trace
    return _make
