import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dvah.models.capability import Capability, CapabilitySet

_caps = st.builds(
    Capability,
    namespace=st.sampled_from(["github", "files", "email", "cloud"]),
    action=st.sampled_from(["read", "write", "delete", "issue.read", "issue.comment"]),
)
_cap_sets = st.builds(
    lambda items: CapabilitySet(caps=frozenset(items)),
    st.lists(_caps, max_size=6),
)


@pytest.mark.invariant("INV-02")
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
@given(requested=_cap_sets, parent=_cap_sets, policy=_cap_sets)
def test_child_capabilities_never_exceed_parent_or_policy(loaded, requested, parent, policy):
    """INV-02: derived child ⊆ parent and child ⊆ policy for all inputs."""
    child = loaded.harness.cfg.capabilities.derive_child(requested, parent, policy)
    assert child.issubset(parent)
    assert child.issubset(policy)
