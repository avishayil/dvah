import pytest


@pytest.mark.adversarial
def test_no_second_foreign_tenant_memory(loaded):
    """A second hostile tenant (rival2) must also be excluded — not just a named allowlist."""
    compiled = loaded.harness.cfg.context_compiler.compile(loaded.root_ctx)
    sources = [item.source for item in compiled.items]
    assert not any(s.startswith("memory:rival2") for s in sources)
    assert compiled.has_untrusted_instruction() is False
