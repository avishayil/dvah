import pytest

from dvah.models.capability import Capability, CapabilitySet

pytestmark = pytest.mark.unit


def test_covers_exact_match():
    assert Capability(namespace="github", action="issue.read").covers("github", "issue.read")


def test_covers_wildcard():
    assert Capability(namespace="github", action="*").covers("github", "anything")


def test_covers_rejects_namespace_mismatch():
    assert not Capability(namespace="github", action="*").covers("files", "read")


def test_covers_rejects_action_mismatch():
    cap = Capability(namespace="github", action="issue.read")
    assert not cap.covers("github", "issue.comment")


def test_permits_any_matching_capability():
    cs = CapabilitySet(caps=frozenset({Capability(namespace="files", action="read")}))
    assert cs.permits("files", "read")
    assert not cs.permits("files", "delete")


def test_intersect_keeps_common_capabilities():
    read = Capability(namespace="files", action="read")
    write = Capability(namespace="files", action="write")
    a = CapabilitySet(caps=frozenset({read, write}))
    b = CapabilitySet(caps=frozenset({read}))
    assert a.intersect(b).caps == frozenset({read})


def test_issubset():
    read = Capability(namespace="files", action="read")
    write = Capability(namespace="files", action="write")
    small = CapabilitySet(caps=frozenset({read}))
    big = CapabilitySet(caps=frozenset({read, write}))
    assert small.issubset(big)
    assert not big.issubset(small)


def test_empty_capability_set_default():
    assert CapabilitySet().caps == frozenset()
