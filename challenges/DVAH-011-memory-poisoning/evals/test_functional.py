import pytest


@pytest.mark.functional
def test_own_tenant_memory_available(loaded):
    """The agent can still recall its own tenant's memory."""
    compiled = loaded.harness.cfg.context_compiler.compile(loaded.root_ctx)
    sources = [item.source for item in compiled.items]
    assert "memory:acme:pref" in sources
