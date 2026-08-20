import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dvah.models.provenance import (
    INSTRUCTION_TRUST_LEVELS,
    ProvenanceRecord,
    ProvenanceTag,
    TrustLevel,
)
from dvah.security.provenance import BuiltinProvenanceTracker

# INV-05 is more than "N tags in → N tags out". A tracker that preserved the *count*
# while corrupting source/tenant/timestamp, mis-routing the instruction-vs-data channel,
# or escalating trust would pass a cardinality-only check yet still break the property.
# We assert each sub-property explicitly (ids used for grading clarity):
#   INV-05.1 cardinality preserved
#   INV-05.2 every input source survives
#   INV-05.3 tenant preserved per tag
#   INV-05.4 timestamp preserved per tag
#   INV-05.5 trust never escalates (data-trust never lands in the instruction channel)

_TRUST_LEVELS = list(TrustLevel)


@pytest.mark.invariant("INV-05")
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
@given(trusts=st.lists(st.sampled_from(_TRUST_LEVELS), min_size=1, max_size=6))
def test_merging_preserves_the_whole_provenance(loaded, trusts):
    """INV-05: merging tags preserves count, source, tenant, timestamp, and channel/trust."""
    tracker = loaded.harness.cfg.provenance
    # Build distinct inputs so we can check each field survived round-trip by source.
    inputs = {}
    record = ProvenanceRecord()
    for i, trust in enumerate(trusts):
        source = f"src{i}"
        tenant = "acme" if i % 2 == 0 else "globex"
        ts = f"2026-01-{i + 1:02d}T00:00:00Z"
        inputs[source] = (trust, tenant, ts)
        tag = tracker.tag_tool_output(source, trust, tenant, ts)
        record = tracker.merge(record, tag)

    all_tags = record.instruction_sources + record.data_sources

    # INV-05.1 cardinality preserved
    assert len(all_tags) == len(trusts), "INV-05.1: a tag was dropped"
    # INV-05.2 every input source survives
    assert {t.source for t in all_tags} == set(inputs), "INV-05.2: a source was lost"
    # INV-05.3 / INV-05.4 tenant + timestamp preserved per tag
    for t in all_tags:
        exp_trust, exp_tenant, exp_ts = inputs[t.source]
        assert t.tenant == exp_tenant, "INV-05.3: tenant corrupted"
        assert t.timestamp == exp_ts, "INV-05.4: timestamp corrupted"
        assert t.trust == exp_trust, "INV-05.x: trust label corrupted"
    # INV-05.5 trust never escalates: instruction channel holds only instruction-trust,
    # and no instruction-trust tag was demoted into the data channel.
    for t in record.instruction_sources:
        assert t.trust in INSTRUCTION_TRUST_LEVELS, "INV-05.5: data escalated to instruction"
    for t in record.data_sources:
        assert t.trust not in INSTRUCTION_TRUST_LEVELS, "INV-05.5: instruction demoted to data"


@pytest.mark.invariant("INV-05")
def test_sub_properties_catch_a_count_preserving_corruptor():
    """A mutant that keeps the count but mis-routes trust must fail the strengthened
    property — proving 05.5 has teeth even when 05.1 (cardinality) still passes."""

    class EscalatingTracker(BuiltinProvenanceTracker):
        # keeps every tag (count preserved) but always files it as an instruction
        def merge(self, record, tag):
            return record.with_instruction(tag)

    tracker = EscalatingTracker()
    record = ProvenanceRecord()
    tag = tracker.tag_tool_output("web", TrustLevel.UNTRUSTED_DATA, "acme",
                                  "2026-01-01T00:00:00Z")
    record = tracker.merge(record, tag)

    # 05.1 cardinality still holds for this mutant...
    assert len(record.instruction_sources) + len(record.data_sources) == 1
    # ...but 05.5 catches the escalation.
    escalated = [t for t in record.instruction_sources
                 if t.trust not in INSTRUCTION_TRUST_LEVELS]
    assert escalated, "expected the escalation to be detectable"
