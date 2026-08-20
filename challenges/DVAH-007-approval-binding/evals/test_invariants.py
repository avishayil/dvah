import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dvah.harness.resolver import build_envelope
from dvah.models.operation import Operation


def _envelope(loaded, resource, params):
    op = Operation(namespace="files", action="delete", resource=resource, parameters=params)
    return build_envelope(loaded.root_ctx, op)


@pytest.mark.invariant("INV-03")
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
@given(
    resource=st.sampled_from(["/a", "/b", "/prod/customer.db"]),
    params=st.dictionaries(st.text(min_size=1, max_size=4), st.text(max_size=4), max_size=3),
)
def test_grant_validates_only_for_its_own_action(loaded, resource, params):
    """INV-03: a grant validates for its exact action and no other."""
    approvals = loaded.harness.cfg.approvals
    env_a = _envelope(loaded, resource, params)
    grant = approvals.request(env_a)
    assert approvals.validate(env_a, grant) is True
    env_b = _envelope(loaded, resource + "-different", {**params, "x": "y"})
    assert approvals.validate(env_b, grant) is False
