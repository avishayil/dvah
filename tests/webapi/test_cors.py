"""CORS is required so the browser UI (:3000) can call the API (:8000)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from dvah.webapi.app import app

pytestmark = pytest.mark.integration

client = TestClient(app)


def test_preflight_allows_cross_origin_call():
    resp = client.options(
        "/api/challenges",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code in (200, 204)
    allowed = resp.headers.get("access-control-allow-origin")
    assert allowed in ("*", "http://localhost:3000")


def test_actual_request_carries_allow_origin_header():
    resp = client.get("/api/challenges", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") in ("*", "http://localhost:3000")
