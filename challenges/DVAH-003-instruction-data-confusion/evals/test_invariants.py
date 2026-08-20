import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dvah.models.observation import Observation
from dvah.models.provenance import TrustLevel

_observations = st.lists(
    st.builds(
        Observation,
        source=st.text(min_size=1, max_size=8),
        trust=st.sampled_from(list(TrustLevel)),
        content=st.just({"noise": "x"}),
    ),
    max_size=5,
)


@pytest.mark.invariant("INV-06")
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=150)
@given(observations=_observations)
def test_compiler_never_puts_untrusted_data_in_instruction_channel(loaded, observations):
    """INV-06: for any observations, the compiled context has no untrusted instruction."""
    ctx = loaded.root_ctx
    for obs in observations:
        ctx = ctx.with_observation(obs)
    compiled = loaded.harness.cfg.context_compiler.compile(ctx)
    assert compiled.has_untrusted_instruction() is False
