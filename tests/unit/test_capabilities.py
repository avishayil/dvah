import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.guardrails.capabilities import BuiltinCapabilityResolver

pytestmark = pytest.mark.unit


def _caps(*pairs):
    return CapabilitySet(caps=frozenset(Capability(namespace=n, action=a) for n, a in pairs))


def test_child_is_intersection_of_all_three():
    resolver = BuiltinCapabilityResolver()
    requested = _caps(("github", "issue.read"), ("github", "issue.comment"))
    parent = _caps(("github", "issue.read"))
    policy = _caps(("github", "issue.read"), ("github", "issue.comment"))
    child = resolver.derive_child(requested, parent, policy)
    assert child.caps == _caps(("github", "issue.read")).caps


def test_child_empty_when_no_overlap():
    resolver = BuiltinCapabilityResolver()
    child = resolver.derive_child(_caps(("a", "x")), _caps(("b", "y")), _caps(("a", "x")))
    assert child.caps == frozenset()
