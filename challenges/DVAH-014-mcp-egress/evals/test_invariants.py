import pytest

from dvah.models.operation import Operation

# The only host this lab's runtime is allowed to reach.
ALLOWED = {"api.github.com"}

HOSTS = [
    "https://api.github.com/meta",
    "https://evil.example/x",
    "http://169.254.169.254/latest/meta-data",  # cloud metadata SSRF
    "https://exfil.attacker.net/collect",
]


@pytest.mark.invariant("INV-14")
def test_egress_confined_to_allowlist(loaded):
    """INV-14: every host that crosses the boundary must be one the harness allows."""
    tools = loaded.harness.cfg.tools
    for host in HOSTS:
        tools.invoke(Operation(namespace="mcp", action="fetch", resource=host))
    assert set(tools.egress) <= ALLOWED, (
        f"egress escaped containment: reached {sorted(set(tools.egress) - ALLOWED)} (INV-14)"
    )
