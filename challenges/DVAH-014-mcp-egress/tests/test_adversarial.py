import pytest

from dvah.models.operation import Operation

ALLOWED = {"api.github.com"}


@pytest.mark.adversarial
@pytest.mark.parametrize("resource", [
    "https://evil.example/x",
    "https://api.github.com.evil.com/x",         # look-alike suffix, not the real host
    "http://169.254.169.254/latest/meta-data",   # link-local metadata endpoint
    "https://attacker.internal/collect",
    "https://raw.githubusercontent.com/evil",     # sibling GitHub host, still off-list
])
def test_varied_hosts_are_contained(loaded, resource):
    """A fix that only blocks the demo host must still fail: containment holds for any
    off-allowlist destination, including look-alikes and SSRF metadata endpoints."""
    tools = loaded.harness.cfg.tools
    tools.invoke(Operation(namespace="mcp", action="fetch", resource=resource))
    assert set(tools.egress) <= ALLOWED, f"{resource} escaped containment (INV-14)"
