"""Cheap security hygiene: challenge-id validation and subprocess env whitelisting."""

from __future__ import annotations

import pytest

from dvah.scenarios import catalog
from dvah.webapi.runner import _child_env

pytestmark = pytest.mark.unit


def test_resolve_valid_id():
    assert catalog.resolve_challenge("DVAH-001").name.startswith("DVAH-001")


def test_resolve_rejects_traversal_id():
    with pytest.raises(LookupError):
        catalog.resolve_challenge("../../etc/passwd")


def test_resolve_rejects_dir_outside_challenges(tmp_path):
    (tmp_path / "scenario.yaml").write_text("id: X\n")
    with pytest.raises(LookupError):
        catalog.resolve_challenge(str(tmp_path))


def test_child_env_withholds_credentials(monkeypatch, tmp_path):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIA-SECRET")
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "bedrock-secret")
    env = _child_env(tmp_path / "r.json")
    for leaked in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_BEARER_TOKEN_BEDROCK"):
        assert leaked not in env
    assert env["DVAH_REPORT"].endswith("r.json")
    assert env["PYTHONUNBUFFERED"] == "1"


def test_bedrock_bearer_env_not_leaked_to_process(monkeypatch):
    import os

    from dvah.providers.bedrock_model import _bearer_env

    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    with _bearer_env("scoped-token"):
        assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "scoped-token"
    assert "AWS_BEARER_TOKEN_BEDROCK" not in os.environ  # restored on exit
