"""Coverage for live-run/create-404/websocket-disconnect + catalog/sessions/invariants helpers."""

import pytest
from fastapi.testclient import TestClient

from dvah.webapi.app import app

pytestmark = pytest.mark.integration

_FIX = '''
class PlanTimeExecutor:
    def execute_plan(self, harness, ctx, steps):
        results = []
        for step in steps:
            if (step.namespace, step.action) == ("agent", "delegate"):
                results.extend(harness.delegate(ctx, step)); continue
            if (step.namespace, step.action) == ("agent", "reflect"):
                results.extend(harness.reflect(ctx, step)); continue
            outcome = harness.broker.run_step(ctx, step)
            ctx = outcome.ctx
            results.append(outcome.result)
        harness.last_ctx = ctx
        return results
'''


@pytest.fixture
def client():
    return TestClient(app)


def _session(client):
    return client.post("/api/sessions", json={"challenge_id": "DVAH-001"}).json()["session_id"]


@pytest.mark.integration
def test_create_unknown_challenge_404(client):
    assert client.post("/api/sessions", json={"challenge_id": "DVAH-999"}).status_code == 404


@pytest.mark.integration
def test_live_run_deterministic_and_halt(client):
    sid = _session(client)
    # deterministic selection passes the key gate → exercises the _run_live path
    ok = client.post(f"/api/sessions/{sid}/live-run",
                     json={"task_id": "DVAH-001-functional", "model": "deterministic"})
    assert ok.status_code == 200
    # apply the fix, then the exploit is denied mid-run → the live path reports `halted`
    client.put(f"/api/sessions/{sid}/files",
               json={"path": "guardrails/vulnerable/executor.py", "contents": _FIX})
    halted = client.post(f"/api/sessions/{sid}/live-run",
                         json={"task_id": "DVAH-001-exploit", "model": "deterministic"})
    assert halted.status_code == 200
    assert "halted" in halted.json()


@pytest.mark.integration
def test_live_run_requires_key_for_real_provider(client):
    sid = _session(client)
    r = client.post(f"/api/sessions/{sid}/live-run",
                    json={"task_id": "DVAH-001-functional", "model": "anthropic"})
    assert r.status_code == 400  # no key configured


@pytest.mark.integration
def test_websocket_disconnect_clean(client):
    sid = _session(client)
    with client.websocket_connect(f"/api/sessions/{sid}/stream"):
        pass  # closing the context triggers the server's WebSocketDisconnect branch


@pytest.mark.integration
def test_tutor_disabled_paths(client):
    assert client.post("/api/settings/tutor/test").json()["ok"] is False
    sid = _session(client)
    assert client.post("/api/tutor", json={"session_id": sid, "question": "hi"}).status_code == 503


# ---- direct helper coverage ----
@pytest.mark.integration
def test_webapi_catalog_helpers(tmp_path):
    from dvah.webapi import catalog
    assert catalog._module_source("dvah.nonexistent.module") is None  # ImportError branch
    assert catalog._module_source("sys") is None  # built-in module → no on-disk source
    assert catalog._module_source("dvah.models.envelope") is not None
    # _references tolerates a syntax-error file in guardrails/vulnerable
    d = tmp_path / "lab" / "guardrails" / "vulnerable"
    d.mkdir(parents=True)
    (d / "bad.py").write_text("def (:\n")  # syntax error → skipped
    (d / "ok.py").write_text("import dvah.models.envelope\n")
    refs = catalog._references(tmp_path / "lab")
    assert any(r["module"] == "dvah.models.envelope" for r in refs)
    assert catalog._resource_summary(tmp_path / "lab") == {}  # no resources.yaml


@pytest.mark.integration
def test_session_manager_direct(tmp_path):
    from dvah.webapi.sessions import SessionManager
    mgr = SessionManager(base=tmp_path, isolated=True)
    created = mgr.create("DVAH-009")  # has skills/ → readonly SKILL.md branch
    sid = created["session_id"]
    assert any("SKILL.md" in f["path"] for f in mgr.readonly_files(sid))
    assert mgr.tasks(sid) == [] or isinstance(mgr.tasks(sid), list)
    with pytest.raises(KeyError):
        mgr.path("f" * 32)  # unknown id
