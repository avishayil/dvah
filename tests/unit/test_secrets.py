import pytest

from dvah.models.operation import Operation
from dvah.guardrails.secrets import BuiltinSecretBroker

pytestmark = pytest.mark.unit


def test_resolve_returns_credential_without_touching_operation():
    broker = BuiltinSecretBroker(credentials={"github": "ghp_secret"})
    op = Operation(namespace="github", action="issue.comment", resource="r")
    assert broker.resolve("github", op) == "ghp_secret"
    # the credential is execution plumbing — it must never enter the operation params
    assert "_credential" not in op.parameters
    assert op.parameters == {}


def test_resolve_is_none_without_credential():
    broker = BuiltinSecretBroker(credentials={})
    op = Operation(namespace="files", action="read", resource="/x")
    assert broker.resolve("files", op) is None


def test_redact_for_model_strips_secret_values():
    broker = BuiltinSecretBroker(credentials={"aws": "AKIA_SECRET"})
    context = ({"note": "hi", "leaked": "AKIA_SECRET"},)
    redacted = broker.redact_for_model(context)
    assert redacted[0] == {"note": "hi"}


def test_redact_masks_secret_embedded_in_larger_string():
    # review #10: a secret must be masked even when it's a substring of a bigger value.
    broker = BuiltinSecretBroker(credentials={"gh": "ghp_abc123"})
    context = ({"header": "Authorization: Bearer ghp_abc123", "note": "token=ghp_abc123!"},)
    redacted = broker.redact_for_model(context)
    assert "ghp_abc123" not in redacted[0]["header"]
    assert redacted[0]["header"] == "Authorization: Bearer ***REDACTED***"
    assert "ghp_abc123" not in redacted[0]["note"]


def test_redact_leaves_non_secret_substrings_untouched():
    broker = BuiltinSecretBroker(credentials={"gh": "ghp_abc123"})
    context = ({"note": "the quick brown fox", "n": 7, "ok": True},)
    redacted = broker.redact_for_model(context)
    assert redacted[0] == {"note": "the quick brown fox", "n": 7, "ok": True}


def test_redact_masks_secrets_nested_in_lists_and_dicts():
    broker = BuiltinSecretBroker(credentials={"aws": "AKIA_SECRET", "gh": "ghp_x"})
    context = (
        {
            "outer": {"inner": "prefix AKIA_SECRET suffix", "safe": "ok"},
            "items": ["ghp_x", "clean", {"deep": "see ghp_x here"}],
        },
    )
    redacted = broker.redact_for_model(context)
    assert redacted[0]["outer"]["inner"] == "prefix ***REDACTED*** suffix"
    assert redacted[0]["outer"]["safe"] == "ok"
    assert redacted[0]["items"][0] == "***REDACTED***"
    assert redacted[0]["items"][1] == "clean"
    assert redacted[0]["items"][2]["deep"] == "see ***REDACTED*** here"
