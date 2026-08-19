"""Settings API: runtime config is editable and secrets are never echoed."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dvah.webapi import settings as settings_mod
from dvah.webapi.app import app

pytestmark = pytest.mark.integration

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_settings():
    # isolate each test from process-global runtime settings
    settings_mod.SETTINGS.__init__()
    yield
    settings_mod.SETTINGS.__init__()


def test_get_settings_shape():
    body = client.get("/api/settings").json()
    assert body["providers"] == ["anthropic", "openai", "bedrock"]
    # Generic model-credential block (shared by tutor + live runs).
    assert set(body["model"]) >= {"ready", "provider", "key_set", "key_hint", "key_source"}
    # Tutor is now just an on/off feature; run mode is a single global choice.
    assert body["tutor"] == {"enabled": False}
    assert body["run_mode"] == "deterministic"
    assert body["run_modes"] == ["deterministic", "live"]
    assert "server" in body and "env_keys" in body


def test_update_sets_provider_and_masks_key():
    body = client.put(
        "/api/settings",
        json={"tutor_enabled": True, "provider": "openai", "api_key": "sk-secret-ABCD"},
    ).json()
    assert body["model"]["provider"] == "openai"
    assert body["tutor"]["enabled"] is True
    assert body["model"]["key_set"] is True
    # only a masked hint is exposed, never the raw key
    assert body["model"]["key_hint"] == "…ABCD"
    assert body["model"]["key_source"] == "ui"


def test_run_mode_is_a_single_global_setting():
    # deterministic by default; live is accepted and persisted.
    assert client.get("/api/settings").json()["run_mode"] == "deterministic"
    body = client.put("/api/settings", json={"run_mode": "live"}).json()
    assert body["run_mode"] == "live"
    # unknown run mode is rejected.
    assert client.put("/api/settings", json={"run_mode": "bogus"}).status_code == 422


def test_raw_key_never_returned_anywhere():
    client.put("/api/settings", json={"provider": "anthropic", "api_key": "sk-topsecret-9999"})
    dump = client.get("/api/settings").text
    assert "sk-topsecret-9999" not in dump
    assert "topsecret" not in dump


def test_unknown_provider_rejected():
    resp = client.put("/api/settings", json={"provider": "not-a-provider"})
    assert resp.status_code == 400


def test_bedrock_accepts_api_key():
    body = client.put(
        "/api/settings",
        json={"tutor_enabled": True, "provider": "bedrock", "api_key": "bedrock-KEY-4321"},
    ).json()
    assert body["model"]["provider"] == "bedrock"
    assert body["model"]["key_set"] is True
    assert body["model"]["key_hint"] == "…4321"
    assert body["model"]["ready"] is True  # a Bedrock API key satisfies readiness
    assert "bedrock-KEY-4321" not in client.get("/api/settings").text


def test_tutor_test_endpoint_reports_not_ready():
    # openai selected, no key configured → not ready. The endpoint returns 200 with a
    # structured {ok:false, error} (a failed/unconfigured call is a normal, actionable
    # outcome the UI shows — not a gateway error), and makes no network call.
    client.put("/api/settings", json={"tutor_enabled": True, "provider": "openai"})
    r = client.post("/api/settings/tutor/test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False and "not enabled" in body["error"]
