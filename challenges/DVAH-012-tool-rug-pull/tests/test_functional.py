import pytest
from dataclasses import replace

from dvah.harness.resolver import build_envelope
from dvah.models.operation import Operation
from dvah.models.runtime import RuntimeContext, SkillRef


def _env(loaded, digest, params=None):
    ctx = loaded.root_ctx
    rt = RuntimeContext(model=ctx.runtime.model, skill=SkillRef(name="github-tool", digest=digest))
    op = Operation(namespace="github", action="issue.comment",
                   resource="repo/acme/payments", parameters=params or {})
    return build_envelope(replace(ctx, runtime=rt), op)


@pytest.mark.functional
def test_approval_still_validates_the_same_tool_and_action(loaded):
    """The legitimate path: a grant validates the exact tool+action it was issued for."""
    approvals = loaded.harness.cfg.approvals
    env = _env(loaded, "sha256:tool-D1")
    grant = approvals.request(env)
    assert approvals.validate(env, grant) is True
