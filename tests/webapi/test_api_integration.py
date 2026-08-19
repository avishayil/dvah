"""Integration tests: the full session → edit → sandboxed run → trace loop."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dvah.webapi.app import app

pytestmark = pytest.mark.integration

# A correct fix for DVAH-001: route every resolved action through the broker gate.
# Class name must stay VulnerableExecutor (the scenario override targets that symbol).
_FIXED_EXECUTOR = '''
_DELEGATE = ("agent", "delegate")
_REFLECT = ("agent", "reflect")


class VulnerableExecutor:
    def execute_plan(self, harness, ctx, steps):
        results = []
        for step in steps:
            if (step.namespace, step.action) == _DELEGATE:
                results.extend(harness.delegate(ctx, step))
                continue
            if (step.namespace, step.action) == _REFLECT:
                results.extend(harness.reflect(ctx, step))
                continue
            outcome = harness.broker.run_step(ctx, step)
            ctx = outcome.ctx
            results.append(outcome.result)
        harness.last_ctx = ctx
        return results
'''


@pytest.fixture
def client():
    return TestClient(app)


def _new_session(client, challenge="DVAH-001") -> str:
    return client.post("/api/sessions", json={"challenge_id": challenge}).json()["session_id"]


def test_original_vulnerable_code_fails_the_suite(client):
    sid = _new_session(client)
    body = client.post(
        f"/api/sessions/{sid}/run", json={"markers": ["exploit", "invariant"]}
    ).json()
    outcomes = {t["outcome"] for t in body["tests"]}
    assert "failed" in outcomes  # the TOCTOU bug is present
    assert body["invariants"]["holding"] < body["invariants"]["total"]


def test_patched_code_passes_and_flips_invariant(client):
    sid = _new_session(client)
    r = client.put(
        f"/api/sessions/{sid}/files",
        json={"path": "vulnerable/executor.py", "contents": _FIXED_EXECUTOR},
    )
    assert r.json() == {"ok": True}
    body = client.post(
        f"/api/sessions/{sid}/run", json={"markers": ["functional", "exploit", "invariant"]}
    ).json()
    assert all(t["outcome"] == "passed" for t in body["tests"]), body["stdout"]
    assert body["invariants"]["holding"] == body["invariants"]["total"] >= 1
    assert body["invariants"]["per"][0] == {"id": "INV-01", "holds": True}


def test_trace_flags_violation_for_vulnerable_and_denies_for_solution(client):
    sid = _new_session(client)
    vuln = client.post(
        f"/api/sessions/{sid}/trace", json={"task_id": "DVAH-001-exploit"}
    ).json()
    assert vuln["summary"]["unauthorized_executions"]  # TOCTOU delete slipped through
    assert any(e["detail"].get("action") == "delete" for e in vuln["events"] if e["kind"] == "executed")

    sol = client.post(
        f"/api/sessions/{sid}/trace",
        json={"task_id": "DVAH-001-exploit", "solution": True},
    ).json()
    assert sol["summary"]["unauthorized_executions"] == []
    assert any(d["invariant"] == "INV-01" for d in sol["summary"]["denials"])


def test_reset_restores_original_code(client):
    sid = _new_session(client)
    client.put(
        f"/api/sessions/{sid}/files",
        json={"path": "vulnerable/executor.py", "contents": _FIXED_EXECUTOR},
    )
    restored = client.post(f"/api/sessions/{sid}/reset").json()["editable_files"]
    executor = next(f for f in restored if f["path"].endswith("executor.py"))
    assert "authorize only the first step" in executor["contents"] or "plan-time" in executor["contents"]


def test_files_endpoint_never_exposes_solution(client):
    sid = _new_session(client, "DVAH-002")
    files = client.get(f"/api/sessions/{sid}/files").json()["files"]
    assert all("solution" not in f["path"] for f in files)
    assert all("FixedCapabilityResolver" not in f["contents"] for f in files)


def test_runner_kills_on_timeout(client):
    """A non-terminating suite is killed by the wall-clock timeout."""
    from dvah.webapi import runner as runner_mod

    sid = _new_session(client)
    session_dir = runner_mod.__dict__  # noqa: F841 - ensure module import
    r = runner_mod.SubprocessRunner(timeout=1)
    # Point the runner at a session whose test hangs: inject a hanging test file.
    from dvah.webapi.app import SESSIONS

    path = SESSIONS.path(sid)
    (path / "tests" / "test_hang.py").write_text(
        "import time, pytest\n"
        "@pytest.mark.exploit\n"
        "def test_hang():\n    time.sleep(30)\n"
    )
    result = r.run(path, ["exploit"])
    assert "timeout" in result["stdout"].lower()
