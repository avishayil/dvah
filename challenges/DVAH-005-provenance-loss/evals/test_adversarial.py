import pytest

from dvah.models.provenance import ProvenanceRecord, TrustLevel


@pytest.mark.adversarial
def test_provenance_survives_many_hops(loaded):
    """No hop may silently drop provenance, no matter how many there are."""
    tracker = loaded.harness.cfg.provenance
    record = ProvenanceRecord()
    for i in range(5):
        tag = tracker.tag_tool_output(f"src-{i}", TrustLevel.UNTRUSTED_DATA, "acme",
                                      "2026-01-01T00:00:00Z")
        record = tracker.merge(record, tag)
    assert len(record.data_sources) == 5
