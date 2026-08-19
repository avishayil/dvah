import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.models.skill import SkillManifest

APPROVED = (Capability(namespace="github", action="issue.read"),)


@pytest.mark.functional
def test_approved_skill_grants_its_permissions(loaded):
    """A skill whose manifest matches the approved/pinned version loads normally."""
    loader = loaded.harness.cfg.skill_loader
    manifest = SkillManifest(name="gh", digest="v1", permissions=APPROVED)
    res = loader.load(manifest, APPROVED, "v1")
    assert res.granted == CapabilitySet(caps=frozenset(APPROVED))
