"""Unit tests for the web API: catalog, hints gating, solution non-leakage, guards."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dvah.webapi.app import app

pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    return TestClient(app)


def test_lists_all_challenges(client):
    body = client.get("/api/challenges").json()
    ids = [c["id"] for c in body["challenges"]]
    assert "DVAH-001" in ids and "DVAH-008" in ids
    assert all("objective" in c and "invariants" in c for c in body["challenges"])


def test_briefing_has_invariant_statements_and_editable_files(client):
    body = client.get("/api/challenges/DVAH-001").json()
    assert body["invariants"][0]["id"] == "INV-01"
    assert body["invariants"][0]["statement"]  # parsed from docs/INVARIANTS.md
    assert any(f["path"].endswith("executor.py") for f in body["editable_files"])
    assert body["tasks"]  # from plans.yaml


def test_unknown_challenge_404(client):
    assert client.get("/api/challenges/DVAH-999").status_code == 404


def test_hint_tiers_are_metadata_only(client):
    idx = client.get("/api/challenges/DVAH-003/hints").json()
    assert idx["count"] >= 1
    assert all(t["revealed"] is False for t in idx["tiers"])
    assert "text" not in idx["tiers"][0]  # text only via the tier endpoint


def test_hint_tier_out_of_range_404(client):
    assert client.get("/api/challenges/DVAH-003/hints/999").status_code == 404


def test_solution_endpoint_reveals_diff(client):
    body = client.get("/api/challenges/DVAH-002/solution").json()
    assert body["files"] and body["diff"]
    assert "AttenuatingCapabilityResolver" in body["files"][0]["contents"]


def test_solution_content_does_not_leak_into_briefing(client):
    # a string that exists only in DVAH-002's SOLUTION, never in briefing/editable files
    briefing = client.get("/api/challenges/DVAH-002").json()
    blob = str(briefing)
    assert "AttenuatingCapabilityResolver" not in blob
    assert "intersect(parent)" not in blob


def test_resources_summary_has_no_secret_values(client):
    # DVAH-004 seeds a secret value; the environment summary must expose keys only,
    # not values (the vulnerable *source* the learner edits may still contain the
    # fixture literal — that is the lab, not a leak).
    briefing = client.get("/api/challenges/DVAH-004").json()
    assert "AKIA-SECRET-123" not in str(briefing["environment"]["resources_summary"])


def test_put_file_rejects_path_traversal(client):
    sid = client.post("/api/sessions", json={"challenge_id": "DVAH-001"}).json()["session_id"]
    for bad in ["../../../etc/passwd.py", "vulnerable/../../evil.py", "solution/executor.py"]:
        r = client.put(f"/api/sessions/{sid}/files", json={"path": bad, "contents": "x"})
        assert r.status_code == 400


def test_mutate_maps_engine_output(client):
    body = client.post("/api/mutate", json={"seed": 1, "count": 2, "reveal": True}).json()
    assert body["total"] == 15  # INV-01..14 (INV-06 split instr/budget; INV-08 attribution)
    assert body["holding"] == 13  # two defeats toggled at seed=1 (INV-14 always holds)
    broken = [p["id"] for p in body["per"] if not p["holds"]]
    assert len(broken) == 2
    assert body["revealed"]


def test_tutor_disabled_by_default(client, monkeypatch):
    monkeypatch.delenv("DVAH_TUTOR", raising=False)
    sid = client.post("/api/sessions", json={"challenge_id": "DVAH-001"}).json()["session_id"]
    r = client.post("/api/tutor", json={"session_id": sid})
    assert r.status_code == 503
