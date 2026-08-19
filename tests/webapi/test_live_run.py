"""Phase A: real-mode key wiring + in-app live run + robust tutor-test errors.

All offline — no live provider is ever called. The live-run path is exercised via the
deterministic fallback (no SDK/key → ModelRouter degrades to the scripted oracle), so this
stays CI-safe while proving the route, gating, and key-threading.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dvah.providers.router_model import _build_live
from dvah.webapi import app as appmod
from dvah.webapi.app import app
from dvah.webapi.settings import SETTINGS

pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_settings(monkeypatch):
    """Isolate the process-global SETTINGS + strip any Bedrock env so gating is deterministic."""
    saved = dict(SETTINGS._api_keys)
    SETTINGS._api_keys.clear()
    for var in ("AWS_BEARER_TOKEN_BEDROCK", "AWS_ACCESS_KEY_ID", "AWS_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    yield
    SETTINGS._api_keys.clear()
    SETTINGS._api_keys.update(saved)


# --- A2: the Settings key reaches the live adapter --------------------------
@pytest.mark.parametrize("provider", ["anthropic", "openai", "bedrock"])
def test_build_live_forwards_api_key(provider):
    adapter = _build_live(provider, None, api_key="secret-token")
    assert adapter._api_key == "secret-token"


def test_build_live_without_key_leaves_env_fallback():
    adapter = _build_live("bedrock", None)
    assert adapter._api_key is None  # adapter falls back to the AWS chain


# --- A3: in-app live run, key-gated -----------------------------------------
def _new_session(client) -> tuple[str, str]:
    s = client.post("/api/sessions", json={"challenge_id": "DVAH-001"}).json()
    task = next(t for t in s["tasks"] if "exploit" in t)
    return s["session_id"], task


def test_live_run_requires_key(client):
    sid, task = _new_session(client)
    r = client.post(f"/api/sessions/{sid}/live-run", json={"task_id": task, "model": "bedrock"})
    assert r.status_code == 400
    assert "Settings" in r.json()["detail"]


def test_live_run_with_key_falls_back_to_deterministic(client):
    # A configured (fake) key passes the gate; with no SDK/real endpoint the live provider
    # errors and the router falls back to the deterministic oracle → a real trace + scores,
    # zero network. Proves the route + key-threading end to end, CI-safe.
    SETTINGS._api_keys["bedrock"] = "fake-token"
    sid, task = _new_session(client)
    r = client.post(f"/api/sessions/{sid}/live-run", json={"task_id": task, "model": "bedrock"})
    assert r.status_code == 200
    body = r.json()
    assert body["events"], "live run produced an agent-timeline trace"
    assert "dual_score" in body
    # DVAH-001 is vulnerable → the deterministic security verdict is not secure.
    assert body["dual_score"]["runtime_security"]["secure"] is False


# --- A1: tutor Test returns a structured error, never a 502 -----------------
def test_tutor_test_returns_structured_error_not_502(client, monkeypatch):
    monkeypatch.setattr(appmod.tutor, "is_enabled", lambda: True)

    def _boom(*a, **k):
        raise RuntimeError("AccessDeniedException: bearer token rejected")

    monkeypatch.setattr(appmod.tutor, "coach", _boom)
    r = client.post("/api/settings/tutor/test")
    assert r.status_code == 200  # not 502 — a failed provider call is a normal outcome
    body = r.json()
    assert body["ok"] is False
    assert "bearer token rejected" in body["error"]


def test_tutor_test_reports_disabled(client, monkeypatch):
    monkeypatch.setattr(appmod.tutor, "is_enabled", lambda: False)
    body = client.post("/api/settings/tutor/test").json()
    assert body["ok"] is False and "not enabled" in body["error"]
