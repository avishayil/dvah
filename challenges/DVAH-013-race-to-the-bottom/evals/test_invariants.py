import pytest


def _patterns(counts):
    """All valid interleavings (as sequences of agent indices), preserving intra-agent order."""
    def rec(remaining):
        if all(r == 0 for r in remaining):
            yield []
            return
        for agent, r in enumerate(remaining):
            if r > 0:
                nxt = list(remaining)
                nxt[agent] -= 1
                for tail in rec(nxt):
                    yield [agent] + tail
    return rec(counts)


@pytest.mark.invariant("INV-12")
def test_no_interleaving_exceeds_limit(loaded):
    """INV-12: under ANY interleaving of two charges, successes never exceed the limit."""
    Tracker = type(loaded.harness.cfg.budget)
    limit = Tracker().remaining()
    ops_per_charge = len(Tracker().steps(None, []))
    agents = 2
    for pattern in _patterns([ops_per_charge] * agents):
        tracker = Tracker()
        out: list = []
        seq = [tracker.steps(None, out) for _ in range(agents)]
        cursor = [0] * agents
        for agent in pattern:
            seq[agent][cursor[agent]]()
            cursor[agent] += 1
        assert out.count("ok") <= limit, f"interleaving {pattern} exceeded the limit (INV-12)"
