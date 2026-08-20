import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dvah.models.capability import Capability, CapabilitySet
from dvah.models.skill import SkillManifest

_caps = st.builds(
    Capability,
    namespace=st.sampled_from(["github", "files", "email", "cloud"]),
    action=st.sampled_from(["read", "write", "delete", "*", "issue.read", "issue.comment"]),
)
_cap_lists = st.lists(_caps, max_size=6)


@pytest.mark.invariant("INV-07")
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
@given(approved=_cap_lists, requested=_cap_lists)
def test_granted_never_exceeds_approved(loaded, approved, requested):
    """INV-07: for any approved/requested pair, the granted caps ⊆ approved."""
    loader = loaded.harness.cfg.skill_loader
    manifest = SkillManifest(name="s", digest="v1", permissions=tuple(requested))
    res = loader.load(manifest, tuple(approved), "v1")
    assert res.granted.issubset(CapabilitySet(caps=frozenset(approved)))
