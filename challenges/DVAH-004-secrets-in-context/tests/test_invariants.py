import pytest

_SECRET = "AKIA-SECRET-123"


@pytest.mark.invariant("INV-04")
def test_secret_stripped_even_when_deeply_nested(loaded):
    """INV-04: no secret value survives redaction, at any nesting depth."""
    context = (
        {"channel": "data", "content": {"a": {"b": [{"cred": _SECRET}]}}},
    )
    out = loaded.harness.cfg.secrets.redact_for_model(context)
    assert _SECRET not in repr(out)
