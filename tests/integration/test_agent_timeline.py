"""Agent-timeline trace events + record/replay + dual-scoring independence (v0.3 Phase 7a).

The new informational events must appear WITHOUT perturbing INV-01 occurrence accounting;
a recorded session must replay to the same verdict with no model calls; and the two scores
must be computed independently.
"""

import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.replay import replay, run_and_record
from dvah.providers.session import ScriptedSession
from dvah.scenarios.catalog import resolve_challenge
from dvah.scenarios.loader import load_challenge
from dvah.scoring import dual_score

pytestmark = pytest.mark.integration


def _caps(*pairs):
    return CapabilitySet(caps=frozenset(Capability(namespace=n, action=a) for n, a in pairs))


def test_agent_timeline_events_emitted_without_perturbing_inv01(make_harness, make_ctx):
    scripts = {"t": [{"namespace": "files", "action": "read", "resource": "/a"}]}
    harness, _files, _gh, trace = make_harness(scripts, files_seed={"/a": "x"})
    ctx = make_ctx(capabilities=_caps(("files", "read")))

    harness.run_task(ctx, "t")

    kinds = {e.kind for e in trace.events}
    for k in ("user.task", "model.request", "model.response", "tool.proposed",
              "observation.received", "agent.finished"):
        assert k in kinds, f"missing timeline event {k}"
    # Timeline events carry no action_hash → complete-mediation accounting is unchanged.
    assert trace.unauthorized_executions() == []


def test_record_then_replay_reproduces_verdict_without_model_calls(tmp_path):
    """Record DVAH-001's scripted exploit, then replay it — the (vulnerable) verdict
    reproduces exactly, driven only by the recorded turns (no model)."""
    cdir = resolve_challenge("DVAH-001")
    loaded = load_challenge(cdir)
    session = ScriptedSession(loaded.harness.cfg.model, "DVAH-001-exploit")
    rec = tmp_path / "session.json"
    data = run_and_record(loaded, "DVAH-001", "DVAH-001-exploit", session, rec)

    out = replay(rec)
    assert out["matches"] is True
    assert out["reproduced"] == data["security"]
    # DVAH-001 vulnerable executes the delete without a fresh authorization.
    assert out["reproduced"]["secure"] is False


def test_dvah001_vulnerable_avoided_yet_insecure():
    """Independence on a real lab: the deterministic run triggers no denial (exercise
    'avoided'), but the vulnerable harness executed unauthorized → Runtime Security ✗."""
    loaded = load_challenge(resolve_challenge("DVAH-001"))
    try:
        loaded.harness.run_task(loaded.root_ctx, "DVAH-001-exploit")
    except Exception:
        pass
    score = dual_score(loaded.trace)
    assert score.security.secure is False


def test_live_experience_exposed_for_dvah003_absent_elsewhere():
    assert load_challenge(resolve_challenge("DVAH-003")).live_experience.get("attack_likelihood")
    assert load_challenge(resolve_challenge("DVAH-001")).live_experience == {}
