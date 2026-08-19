import pytest

from dvah.models.provenance import TrustLevel


@pytest.mark.invariant("INV-10")
def test_memory_is_tenant_scoped_and_informational(loaded):
    """INV-10: memory items stay in the data channel and no foreign tenant leaks in."""
    compiled = loaded.harness.cfg.context_compiler.compile(loaded.root_ctx)
    for item in compiled.items:
        if item.trust == TrustLevel.MEMORY:
            assert item.channel == "data"  # never an instruction
        assert not item.source.startswith("memory:rival")  # no cross-tenant memory
