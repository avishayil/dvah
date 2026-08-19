"""WebSocket streaming, session lifecycle (DELETE + TTL), and error surfacing."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dvah.webapi.app import app
from dvah.webapi.sessions import SessionManager

pytestmark = pytest.mark.integration

client = TestClient(app)


def _session() -> str:
    return client.post("/api/sessions", json={"challenge_id": "DVAH-001"}).json()["session_id"]


def test_ws_streams_run_to_done():
    sid = _session()
    with client.websocket_connect(f"/api/sessions/{sid}/stream") as ws:
        ws.send_json({"markers": ["exploit"]})
        kinds = []
        while True:
            msg = ws.receive_json()
            kinds.append(msg["type"])
            if msg["type"] == "done":
                assert isinstance(msg["result"]["tests"], list)
                break
    assert "done" in kinds


def test_ws_rejects_invalid_markers():
    sid = _session()
    with client.websocket_connect(f"/api/sessions/{sid}/stream") as ws:
        ws.send_json({"markers": ["bogus-marker"]})
        assert ws.receive_json()["type"] == "error"


def test_delete_session_removes_it():
    sid = _session()
    assert client.delete(f"/api/sessions/{sid}").status_code == 200
    assert client.get(f"/api/sessions/{sid}/files").status_code == 404


def test_broken_code_surfaces_an_error_not_zero_tests():
    sid = _session()
    client.put(
        f"/api/sessions/{sid}/files",
        json={"path": "vulnerable/executor.py", "contents": "def (syntax error"},
    )
    res = client.post(f"/api/sessions/{sid}/run", json={"markers": ["exploit"]}).json()
    assert res["tests"], "a broken edit must surface tests, not an empty list"
    assert any(t["outcome"] in ("error", "failed") for t in res["tests"])


def test_session_manager_ttl_reaps(tmp_path):
    mgr = SessionManager(base=tmp_path, ttl=0)
    sid = mgr.create("DVAH-001")["session_id"]
    with pytest.raises(KeyError):
        mgr.path(sid)  # ttl=0 → immediately expired
