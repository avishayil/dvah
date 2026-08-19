import pytest

from dvah.models.provenance import (
    INSTRUCTION_TRUST_LEVELS,
    ProvenanceRecord,
    ProvenanceTag,
    TrustLevel,
)

pytestmark = pytest.mark.unit


def _tag(trust):
    return ProvenanceTag(source="s", trust=trust, tenant="acme", timestamp="2026-01-01T00:00:00Z")


def test_instruction_trust_levels_membership():
    assert TrustLevel.USER_INSTRUCTION in INSTRUCTION_TRUST_LEVELS
    assert TrustLevel.TRUSTED_INSTRUCTION in INSTRUCTION_TRUST_LEVELS
    assert TrustLevel.UNTRUSTED_DATA not in INSTRUCTION_TRUST_LEVELS


def test_with_data_appends_and_is_immutable():
    rec = ProvenanceRecord()
    rec2 = rec.with_data(_tag(TrustLevel.UNTRUSTED_DATA))
    assert len(rec2.data_sources) == 1
    assert rec.data_sources == ()


def test_with_instruction_appends():
    rec = ProvenanceRecord().with_instruction(_tag(TrustLevel.USER_INSTRUCTION))
    assert len(rec.instruction_sources) == 1


def test_tag_carries_optional_integrity():
    tag = ProvenanceTag(source="s", trust=TrustLevel.MEMORY, tenant="acme",
                        timestamp="t", integrity="sha256:abc")
    assert tag.integrity == "sha256:abc"
