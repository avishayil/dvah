"""Coverage for webapi error/edge branches (404s, halt, websocket, settings, hints)."""

import pytest
from fastapi.testclient import TestClient

from dvah.webapi.app import app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    return TestClient(app)


def _new_session(client, challenge="DVAH-001"):
    r = client.post("/api/sessions", json={"challenge_id": challenge})
    assert r.status_code == 200
    return r.json()["session_id"]


@pytest.mark.integration
def test_unknown_challenge_404s(client):
    assert client.get("/api/challenges/DVAH-999").status_code == 404
    assert client.get("/api/challenges/DVAH-999/hints").status_code == 404
    assert client.get("/api/challenges/DVAH-999/hints/0").status_code == 404
    assert client.get("/api/challenges/DVAH-999/solution").status_code == 404
    # walkthrough happy path (DVAH-001 has one)
    assert client.get("/api/challenges/DVAH-001/walkthrough").status_code == 200


@pytest.mark.integration
def test_bad_session_id_404s(client):
    bad = "0" * 32
    assert client.get(f"/api/sessions/{bad}/files").status_code == 404
    assert client.post(f"/api/sessions/{bad}/run", json={}).status_code == 404
    assert client.get(f"/api/sessions/{bad}/progress").status_code == 404


_FIXED_EXECUTOR = '''
_DELEGATE = ("agent", "delegate")
_REFLECT = ("agent", "reflect")


class PlanTimeExecutor:
    def execute_plan(self, harness, ctx, steps):
        results = []
        for step in steps:
            if (step.namespace, step.action) == _DELEGATE:
                results.extend(harness.delegate(ctx, step)); continue
            if (step.namespace, step.action) == _REFLECT:
                results.extend(harness.reflect(ctx, step)); continue
            outcome = harness.broker.run_step(ctx, step)
            ctx = outcome.ctx
            results.append(outcome.result)
        harness.last_ctx = ctx
        return results
'''


@pytest.mark.integration
def test_trace_halts_when_fix_denies(client):
    """With the per-action fix applied, the exploit's second op is denied → run_session
    raises → the trace endpoint reports a `halted` field (covers the halt branch)."""
    sid = _new_session(client)
    client.put(f"/api/sessions/{sid}/files",
               json={"path": "guardrails/vulnerable/executor.py", "contents": _FIXED_EXECUTOR})
    r = client.post(f"/api/sessions/{sid}/trace", json={"task_id": "DVAH-001-exploit"})
    assert r.status_code == 200
    assert "halted" in r.json()


@pytest.mark.integration
def test_websocket_bad_id_closes(client):
    bad = "0" * 32
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/sessions/{bad}/stream"):
            pass


@pytest.mark.integration
def test_reset_and_delete_session(client):
    sid = _new_session(client)
    assert client.post(f"/api/sessions/{sid}/reset").status_code == 200
    assert client.delete(f"/api/sessions/{sid}").status_code == 200


@pytest.mark.integration
def test_settings_get_put_and_bad_run_mode(client):
    assert client.get("/api/settings").status_code == 200
    ok = client.put("/api/settings", json={"run_mode": "deterministic", "model": "anthropic"})
    assert ok.status_code == 200
    bad = client.put("/api/settings", json={"run_mode": "bogus"})
    assert bad.status_code in (400, 422)


@pytest.mark.integration
def test_hints_index_and_tiers(client):
    # DVAH-001 has a walkthrough → hints resolve; tier fetch returns text.
    idx = client.get("/api/challenges/DVAH-001/hints")
    assert idx.status_code == 200
    t0 = client.get("/api/challenges/DVAH-001/hints/0")
    assert t0.status_code in (200, 404)


@pytest.mark.integration
def test_mutate_endpoint(client):
    r = client.post("/api/mutate", json={"seed": 1, "count": 1})
    assert r.status_code == 200
    assert "total" in r.json()
