import pytest

_SECRET = "AKIA-SECRET-123"


@pytest.mark.adversarial
def test_secret_is_stripped_however_it_is_nested(loaded):
    """Redaction must reach secrets nested in dicts and lists, not just top level."""
    context = (
        {"channel": "data", "content": {"contents": _SECRET}},
        {"channel": "data", "content": {"nested": {"key": _SECRET}}},
        {"channel": "data", "content": {"items": [_SECRET, "harmless"]}},
    )
    redacted = loaded.harness.cfg.secrets.redact_for_model(context)
    assert _SECRET not in repr(redacted)
