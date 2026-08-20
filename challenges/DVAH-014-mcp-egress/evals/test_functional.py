import pytest

from dvah.models.operation import Operation

APPROVED = "https://api.github.com/repos/acme/app"


@pytest.mark.functional
def test_approved_fetch_succeeds(loaded):
    """An approved host is reachable through the MCP boundary for both configs."""
    tools = loaded.harness.cfg.tools
    result = tools.invoke(Operation(namespace="mcp", action="fetch", resource=APPROVED))
    assert result.ok
    # Exact host-set equality (not a URL substring check): the only host the boundary
    # crossed is the approved one.
    assert set(tools.egress) == {"api.github.com"}
    assert "contents-of://api.github.com" in result.output["content"]
