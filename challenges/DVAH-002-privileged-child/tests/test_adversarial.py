import pytest

from dvah.models.capability import Capability, CapabilitySet


def _caps(*actions):
    return CapabilitySet(caps=frozenset(Capability(namespace="github", action=a) for a in actions))


@pytest.mark.adversarial
@pytest.mark.parametrize("extra", ["issue.comment", "repository.delete", "workflow.modify"])
def test_child_stays_within_parent_for_any_overreach(loaded, extra):
    """Attenuation must clamp to the parent regardless of what the child requests."""
    parent = _caps("issue.read")
    requested = _caps("issue.read", extra)
    child = loaded.harness.cfg.capabilities.derive_child(requested, parent, requested)
    assert child.issubset(parent)
