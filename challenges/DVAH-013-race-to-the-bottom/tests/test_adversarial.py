import pytest


@pytest.mark.adversarial
@pytest.mark.parametrize("agents", [2, 3, 5])
def test_extra_concurrency_never_bypasses_limit(loaded, agents):
    """More concurrent agents must not buy more successful charges than the limit (INV-12)."""
    Tracker = type(loaded.harness.cfg.budget)
    limit = Tracker().remaining()
    tracker = Tracker()
    out: list = []
    seq = [tracker.steps(None, out) for _ in range(agents)]
    ops_per_charge = len(seq[0])
    # Worst-case interleave: every agent runs phase 0, then everyone runs phase 1, …
    for phase in range(ops_per_charge):
        for agent in range(agents):
            seq[agent][phase]()
    assert out.count("ok") <= limit, (
        f"{out.count('ok')} of {agents} agents charged past a limit of {limit} (INV-12)"
    )
