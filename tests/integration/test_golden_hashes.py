"""Determinism tripwire (Phase 0 characterization).

Pins the exact ordered ``action_hash`` sequence each lab's reference solution produces for
every task in its ``plans.yaml``. The reference-architecture restructure must never change a
hash input (actor/agent_id, namespace, action, resource, params, delegation chain, tenant), so
these fingerprints must stay byte-identical through every phase. A diff here means a supposedly
behavior-preserving move actually perturbed authorization identity — stop and investigate.

Regenerate intentionally (only when a hash change is genuinely intended) by running the helper
in this module's ``__main__`` and pasting the output into ``GOLDEN``.
"""

from __future__ import annotations

import hashlib

import pytest
import yaml

from dvah.scenarios.catalog import scenario_dirs
from dvah.scenarios.loader import load_challenge
from dvah.security.decision import Denied

# lab dir name -> {task_id: sha256(action_hash sequence)[:16]}
GOLDEN = {
    "DVAH-001-plan-time-authorization": {
        "DVAH-001-adversarial": "db1a72cc918ab375",
        "DVAH-001-exploit": "82dd5134d7ad0804",
        "DVAH-001-functional": "202c68d34aa6975e",
    },
    "DVAH-002-privileged-child": {
        "DVAH-002-child-comment": "3730bd3e7a26ef92",
        "DVAH-002-child-read": "71b4e1f101b25179",
        "DVAH-002-exploit": "9c1bb58bfe93cb30",
        "DVAH-002-functional": "b5ab07263f5ac4a4",
    },
    "DVAH-003-instruction-data-confusion": {
        "DVAH-003-exploit": "71b4e1f101b25179",
        "DVAH-003-functional": "71b4e1f101b25179",
    },
    "DVAH-004-secrets-in-context": {
        "DVAH-004-exploit": "702977c0c234d1f8",
        "DVAH-004-functional": "d0009e57134cde7a",
    },
    "DVAH-005-provenance-loss": {
        "DVAH-005-exploit": "71b4e1f101b25179",
        "DVAH-005-functional": "71b4e1f101b25179",
    },
    "DVAH-006-infinite-delegation": {
        "DVAH-006-child": "f0cd0117b34cabe3",
        "DVAH-006-exploit": "09aafd063b611d0e",
        "DVAH-006-functional": "d38174d14ac4bcc3",
        "DVAH-006-grandchild": "bfe690fed275e7eb",
    },
    "DVAH-007-approval-binding": {
        "DVAH-007-exploit": "1bc9288395e4f9ae",
        "DVAH-007-functional": "c28ac9dc2419a027",
    },
    "DVAH-008-tool-vs-operation": {
        "DVAH-008-exploit": "1b9e2b58b89f79bf",
        "DVAH-008-functional": "9cf642b3374a1c38",
    },
    "DVAH-009-skill-upgrade": {},
    "DVAH-010-continuous-authorization": {
        "DVAH-010-adversarial": "21c6c28328269471",
        "DVAH-010-exploit": "f8bae3520d5b71ed",
        "DVAH-010-functional": "5d4f91c90ff03fd8",
    },
    "DVAH-011-memory-poisoning": {
        "DVAH-011-exploit": "e3b0c44298fc1c14",
        "DVAH-011-functional": "e3b0c44298fc1c14",
    },
    "DVAH-012-tool-rug-pull": {"DVAH-012-noop": "59309204bad3bd89"},
    "DVAH-013-race-to-the-bottom": {"DVAH-013-noop": "7742061da8e9f56b"},
    "DVAH-014-mcp-egress": {"DVAH-014-noop": "60f27c80c2ca4cef"},
}

_LAB_DIRS = {d.name: d for d in scenario_dirs()}


def _fingerprints(challenge_dir) -> dict:
    plans = challenge_dir / "environment" / "plans.yaml"
    if not plans.exists():
        # After the restructure the deterministic fixture lives under workflows/.
        plans = challenge_dir / "workflows" / "plans.yaml"
    tasks = list((yaml.safe_load(plans.read_text()) or {}).keys()) if plans.exists() else []
    result = {}
    for task_id in tasks:
        loaded = load_challenge(challenge_dir, use_solution=True)
        try:
            loaded.harness.run_task(loaded.root_ctx, task_id)
        except Denied:
            pass  # a denial is a valid outcome; we fingerprint whatever resolved
        hashes = [e.action_hash for e in loaded.trace.events if e.action_hash]
        result[task_id] = hashlib.sha256("|".join(hashes).encode()).hexdigest()[:16]
    return result


@pytest.mark.integration
@pytest.mark.parametrize("lab", sorted(GOLDEN), ids=sorted(GOLDEN))
def test_action_hash_sequence_is_unchanged(lab):
    assert _fingerprints(_LAB_DIRS[lab]) == GOLDEN[lab]


if __name__ == "__main__":  # regeneration helper
    import json

    print(json.dumps({name: _fingerprints(d) for name, d in sorted(_LAB_DIRS.items())}, indent=2))
