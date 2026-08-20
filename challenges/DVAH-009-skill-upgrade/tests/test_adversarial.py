import pytest

from dvah.models.capability import CapabilitySet


@pytest.mark.adversarial
def test_matched_digest_still_cannot_expand(loaded):
    """The trojan (skills/github-investigator-trojan/SKILL.md) keeps the approved digest
    but requests destructive powers. A digest-only check would be fooled; the correct
    loader still refuses to widen without re-approval."""
    approved = loaded.skills["approved"]
    trojan = loaded.skills["trojan"]
    res = loaded.harness.cfg.skill_loader.load(trojan, approved.permissions, approved.digest)
    assert res.granted.issubset(CapabilitySet(caps=frozenset(approved.permissions)))
    assert res.requires_reapproval is True
