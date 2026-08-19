"""RPC learner/grader split (review #7 residual).

Verifies (a) the learner-server workspace contains NO tests/ and NO solution/, (b) the
RpcAdapter<->AdapterServer round-trips HarnessAdapter calls over stdio, and (c) grading the
invariant battery across the process boundary yields correct verdicts — a vulnerable
submission breaks its invariant, the reference solution holds.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from dvah.grading import assemble_server_workspace, grade_rpc
from dvah.grading.rpc import RpcAdapter
from dvah.models.capability import Capability, CapabilitySet
from dvah.scenarios import catalog

pytestmark = pytest.mark.integration

CAP = lambda n, a: CapabilitySet(caps=frozenset({Capability(namespace=n, action=a)}))


def _server_workspace(challenge_id: str, use_solution: bool) -> Path:
    source = catalog.resolve_challenge(challenge_id)
    dest = Path(tempfile.mkdtemp(prefix="dvah-rpc-test-"))
    assemble_server_workspace(source, dest, code_dir=None, use_solution=use_solution)
    return dest


def test_learner_server_workspace_has_no_tests_or_solution():
    ws = _server_workspace("DVAH-001-plan-time-authorization", use_solution=False)
    names = {p.name for p in ws.iterdir()}
    assert "vulnerable" in names and "environment" in names and "scenario.yaml" in names
    assert "tests" not in names, "hidden tests must not be on the learner-executed filesystem"
    assert "solution" not in names, "reference solution must not coexist with learner code"


def test_reference_server_workspace_has_solution_not_learner_code():
    ws = _server_workspace("DVAH-001-plan-time-authorization", use_solution=True)
    names = {p.name for p in ws.iterdir()}
    assert "solution" in names and "vulnerable" not in names and "tests" not in names


def test_rpc_adapter_round_trips_over_stdio():
    ws = _server_workspace("DVAH-002-privileged-child", use_solution=True)
    adapter = RpcAdapter(ws, use_solution=True)
    try:
        # A method with a structured return: attenuation must never widen beyond the parent.
        parent = CAP("github", "issue.read")
        child = adapter.derive_child(
            CapabilitySet(caps=parent.caps | {Capability(namespace="github", action="issue.comment")}),
            parent,
            CapabilitySet(caps=parent.caps | {Capability(namespace="github", action="issue.comment")}),
        )
        assert child.issubset(parent)
        # A scalar return crossing the boundary.
        assert adapter.external_tool_trust("trusted_instruction") == "untrusted_data"
    finally:
        adapter.close()


def test_rpc_grade_solution_holds_vulnerable_breaks():
    # DVAH-002 breaks INV-02 (capability attenuation) in its vulnerable capability resolver.
    sol = grade_rpc("DVAH-002-privileged-child", code_dir=None, use_solution=True)
    assert sol["passed"], f"reference solution should hold all invariants: {sol['broken']}"

    vuln = grade_rpc("DVAH-002-privileged-child", code_dir=None, use_solution=False)
    assert not vuln["passed"], "vulnerable submission must fail at least one invariant"
    assert "INV-02" in vuln["broken"], f"expected INV-02 broken, got {vuln['broken']}"


def test_loaded_adapter_battery_in_process():
    """The LoadedHarnessAdapter (what the RPC server wraps) drives the whole battery in-process:
    a solution holds every invariant; a vulnerable resolver breaks its own one."""
    from dvah.conformance.battery import run_battery
    from dvah.conformance.loaded_adapter import LoadedHarnessAdapter
    from dvah.scenarios.loader import load_challenge

    src = catalog.resolve_challenge("DVAH-002-privileged-child")
    holds_sol = run_battery(LoadedHarnessAdapter(load_challenge(src, use_solution=True)))
    assert holds_sol.passed, f"solution broke: {holds_sol.broken}"

    holds_vuln = run_battery(LoadedHarnessAdapter(load_challenge(src, use_solution=False)))
    assert "INV-02" in holds_vuln.broken
