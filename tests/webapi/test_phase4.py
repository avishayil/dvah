"""Phase 4: server-enforced learn/ctf, progress log, and tutor context wiring."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dvah.webapi import tutor as tutor_mod
from dvah.webapi.app import SESSIONS, app

pytestmark = pytest.mark.integration

client = TestClient(app)


def _session(mode: str) -> str:
    resp = client.post("/api/sessions", json={"challenge_id": "DVAH-001", "mode": mode})
    assert resp.status_code == 200
    return resp.json()["session_id"]


def test_ctf_locks_hints_and_solution_but_not_walkthrough():
    sid = _session("ctf")
    assert client.get(f"/api/challenges/DVAH-001/hints?session_id={sid}").status_code == 403
    assert client.get(f"/api/challenges/DVAH-001/hints/0?session_id={sid}").status_code == 403
    assert client.get(f"/api/challenges/DVAH-001/solution?session_id={sid}").status_code == 403
    assert client.get("/api/challenges/DVAH-001/walkthrough").status_code == 200


def test_learn_session_allows_hints():
    sid = _session("learn")
    assert client.get(f"/api/challenges/DVAH-001/hints?session_id={sid}").status_code == 200
    assert client.get(f"/api/challenges/DVAH-001/hints/0?session_id={sid}").status_code == 200


def test_no_session_id_is_unlocked():
    # CLI / direct callers pass no session_id → behaves as learn.
    assert client.get("/api/challenges/DVAH-001/hints").status_code == 200
    assert client.get("/api/challenges/DVAH-001/solution").status_code == 200


def test_progress_records_hint_and_run():
    sid = _session("learn")
    client.get(f"/api/challenges/DVAH-001/hints/0?session_id={sid}")
    # record a run directly (avoids a heavy pytest subprocess in the test)
    SESSIONS.record_run(
        sid, {"tests": [{"name": "t_a", "outcome": "failed"}], "invariants": {"holding": 0, "total": 1}}
    )
    prog = client.get(f"/api/sessions/{sid}/progress").json()
    assert prog["mode"] == "learn"
    assert prog["hints_revealed"] >= 1
    assert prog["runs"] == 1
    assert any(e.get("kind") == "hint_revealed" for e in prog["events"])
    assert any(e.get("kind") == "run" for e in prog["events"])


def test_first_all_green_is_stamped():
    sid = _session("learn")
    SESSIONS.record_run(
        sid, {"tests": [{"name": "t", "outcome": "passed"}], "invariants": {"holding": 1, "total": 1}}
    )
    prog = client.get(f"/api/sessions/{sid}/progress").json()
    assert prog["time_to_first_all_green_s"] is not None


def test_tutor_receives_stored_failing_and_trace(monkeypatch):
    sid = _session("learn")
    SESSIONS.record_run(
        sid, {"tests": [{"name": "test_x", "outcome": "failed"}], "invariants": {"holding": 0, "total": 1}}
    )
    SESSIONS.record_trace(sid, {"unauthorized_executions": ["h1"]})
    captured: dict = {}

    def fake_coach(code, failing, trace_summary, question):
        captured["failing"] = failing
        captured["trace"] = trace_summary
        return "nudge"

    monkeypatch.setattr(tutor_mod, "is_enabled", lambda: True)
    monkeypatch.setattr(tutor_mod, "coach", fake_coach)
    resp = client.post("/api/tutor", json={"session_id": sid, "question": "help"})
    assert resp.status_code == 200
    assert captured["failing"] == ["test_x"]
    assert captured["trace"] == {"unauthorized_executions": ["h1"]}
