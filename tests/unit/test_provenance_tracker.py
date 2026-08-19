import pytest

from dvah.models.provenance import ProvenanceRecord, TrustLevel
from dvah.security.provenance import BuiltinProvenanceTracker

pytestmark = pytest.mark.unit

CLOCK = "2026-01-01T00:00:00Z"


def test_tag_tool_output_fields():
    tag = BuiltinProvenanceTracker().tag_tool_output("github:issue", TrustLevel.UNTRUSTED_DATA, "acme", CLOCK)
    assert tag.source == "github:issue"
    assert tag.trust is TrustLevel.UNTRUSTED_DATA
    assert tag.tenant == "acme"
    assert tag.timestamp == CLOCK


def test_merge_routes_data_to_data_sources():
    tracker = BuiltinProvenanceTracker()
    tag = tracker.tag_tool_output("s", TrustLevel.UNTRUSTED_DATA, "acme", CLOCK)
    rec = tracker.merge(ProvenanceRecord(), tag)
    assert len(rec.data_sources) == 1
    assert rec.instruction_sources == ()


def test_merge_routes_instruction_to_instruction_sources():
    tracker = BuiltinProvenanceTracker()
    tag = tracker.tag_tool_output("s", TrustLevel.USER_INSTRUCTION, "acme", CLOCK)
    rec = tracker.merge(ProvenanceRecord(), tag)
    assert len(rec.instruction_sources) == 1


def test_has_untrusted_instruction_detects_leak():
    tracker = BuiltinProvenanceTracker()
    untrusted = tracker.tag_tool_output("s", TrustLevel.UNTRUSTED_DATA, "acme", CLOCK)
    leaked = ProvenanceRecord().with_instruction(untrusted)
    assert tracker.has_untrusted_instruction(leaked)


def test_has_untrusted_instruction_false_when_clean():
    tracker = BuiltinProvenanceTracker()
    trusted = tracker.tag_tool_output("s", TrustLevel.USER_INSTRUCTION, "acme", CLOCK)
    clean = ProvenanceRecord().with_instruction(trusted)
    assert not tracker.has_untrusted_instruction(clean)
