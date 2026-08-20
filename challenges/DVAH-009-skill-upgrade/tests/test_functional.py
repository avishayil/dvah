import pytest

from dvah.models.capability import CapabilitySet


@pytest.mark.functional
def test_approved_skill_grants_its_permissions(loaded):
    """The approved, pinned skill (from skills/github-investigator/SKILL.md) loads normally."""
    approved = loaded.skills["approved"]
    loader = loaded.harness.cfg.skill_loader
    res = loader.load(approved, approved.permissions, approved.digest)
    assert res.granted == CapabilitySet(caps=frozenset(approved.permissions))
    assert res.requires_reapproval is False
