import pytest
from dataclasses import replace
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from dvah.harness.resolver import build_envelope
from dvah.models.operation import Operation
from dvah.models.runtime import RuntimeContext, SkillRef


def _env(loaded, digest, params):
    ctx = loaded.root_ctx
    rt = RuntimeContext(model=ctx.runtime.model, skill=SkillRef(name="github-tool", digest=digest))
    op = Operation(namespace="github", action="issue.comment",
                   resource="repo/acme/payments", parameters=params)
    return build_envelope(replace(ctx, runtime=rt), op)


@pytest.mark.invariant("INV-11")
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=150)
@given(
    d1=st.text(min_size=1, max_size=6),
    d2=st.text(min_size=1, max_size=6),
    params=st.dictionaries(st.text(min_size=1, max_size=3), st.text(max_size=3), max_size=2),
)
def test_grant_binds_to_the_tool_digest(loaded, d1, d2, params):
    """INV-11: a grant validates an action iff its full hash (incl. tool digest) matches."""
    approvals = loaded.harness.cfg.approvals
    grant = approvals.request(_env(loaded, f"sha256:{d1}", params))
    assert approvals.validate(_env(loaded, f"sha256:{d1}", params), grant) is True
    if d1 != d2:
        assert approvals.validate(_env(loaded, f"sha256:{d2}", params), grant) is False
