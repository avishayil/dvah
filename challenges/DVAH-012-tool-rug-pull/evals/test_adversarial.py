import pytest
from dataclasses import replace

from dvah.harness.resolver import build_envelope
from dvah.models.operation import Operation
from dvah.models.runtime import RuntimeContext, SkillRef


def _env(loaded, digest):
    ctx = loaded.root_ctx
    rt = RuntimeContext(model=ctx.runtime.model, skill=SkillRef(name="github-tool", digest=digest))
    op = Operation(namespace="github", action="issue.comment", resource="repo/acme/payments")
    return build_envelope(replace(ctx, runtime=rt), op)


@pytest.mark.adversarial
@pytest.mark.parametrize("evil", ["sha256:D2", "sha256:D3", "sha256:latest", "sha256:"])
def test_no_swapped_tool_digest_is_accepted(loaded, evil):
    """A grant for D1 must reject the operation under ANY other tool digest."""
    approvals = loaded.harness.cfg.approvals
    grant = approvals.request(_env(loaded, "sha256:D1"))
    assert not approvals.validate(_env(loaded, evil), grant)
    assert approvals.validate(_env(loaded, "sha256:D1"), grant)  # exact match still ok
