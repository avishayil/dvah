"""Environment files are exposed to the editor as read-only tabs, with resources
values withheld so secret material never leaves the server."""

import pytest

from dvah.webapi.sessions import SessionManager

_CHALLENGE = "DVAH-004-secrets-in-context"
_SECRET = "AKIA-SECRET-123"  # a value inside DVAH-004's resources.yaml


@pytest.mark.integration
def test_session_exposes_environment_as_readonly(tmp_path):
    mgr = SessionManager(base=tmp_path)
    s = mgr.create(_CHALLENGE)

    # editable vulnerable file(s) are writable
    assert s["editable_files"]
    assert all(f["writable"] is True for f in s["editable_files"])
    assert all(f["path"].startswith("guardrails/vulnerable/") for f in s["editable_files"])

    ro = {f["path"]: f for f in s["readonly_files"]}
    # users/agents surfaced verbatim + the scripted workflow (plans); all not writable
    assert "environment/users.yaml" in ro
    assert "environment/agents.yaml" in ro
    assert "workflows/plans.yaml" in ro
    assert all(f["writable"] is False for f in s["readonly_files"])


@pytest.mark.integration
def test_resources_are_values_withheld(tmp_path):
    mgr = SessionManager(base=tmp_path)
    s = mgr.create(_CHALLENGE)
    ro = {f["path"]: f for f in s["readonly_files"]}

    res = ro["environment/resources.yaml"]["contents"]
    # keys are shown (namespaces), but the secret VALUE must never appear
    assert "files:" in res
    assert "secrets:" in res
    assert _SECRET not in res, "secret value leaked into the read-only environment tab"
    assert "values withheld" in res
