"""Final coverage: intentionally-broken components, session-manager branches, catalog/invariants edges."""

import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.models.operation import Operation
from dvah.models.runtime import Constraints


# ---------------- intentionally-broken components (mutation/broken.py) ----------------
@pytest.mark.unit
def test_broken_approval_find_returns_first():
    from dvah.mutation.broken import DigestBlindApprovalService, PlanBoundApprovalService
    g = object()
    assert PlanBoundApprovalService().find([g], None) is g
    assert DigestBlindApprovalService().find([g], None) is g
    assert PlanBoundApprovalService().find([], None) is None


@pytest.mark.unit
def test_broken_provenance_and_budgets():
    from dvah.mutation.broken import DroppingProvenanceTracker, PerAgentBudgetTracker, RacyBudgetTracker
    from dvah.guardrails.decision import Denied
    assert DroppingProvenanceTracker().has_untrusted_instruction(object()) is False

    class Ctx:
        actions_used = 0
        constraints = Constraints(max_actions=0)
    with pytest.raises(Denied):
        PerAgentBudgetTracker().charge(Ctx())
    assert PerAgentBudgetTracker().remaining() == 1

    racy = RacyBudgetTracker(limit=1)
    racy.charge(object())            # first ok → used=1
    assert racy.remaining() == 0
    with pytest.raises(Denied):
        racy.charge(object())        # second past the limit


@pytest.mark.unit
def test_broken_policies_deny_branches(make_envelope):
    from dvah.mutation.broken import NoAttributionPolicy, ToolNamePolicy
    op = Operation(namespace="github", action="issue.read", resource="acme/app")
    permitted = make_envelope(operation=op,
                              capabilities=CapabilitySet(caps=frozenset({Capability(namespace="github", action="issue.read")})))
    denied = make_envelope(operation=op, capabilities=CapabilitySet())
    assert ToolNamePolicy().authorize(permitted).reason.startswith("tool namespace")
    assert ToolNamePolicy().authorize(denied).invariant == "INV-13"
    assert NoAttributionPolicy().authorize(denied).invariant == "INV-01"
    assert NoAttributionPolicy().authorize(permitted).reason == "attribution not verified"


# ---------------- session manager branches ----------------
@pytest.mark.unit
def test_sessions_tasks_empty(tmp_path):
    from dvah.webapi.sessions import _tasks
    assert _tasks(tmp_path) == []  # no workflows/ or environment/ plans


@pytest.mark.unit
def test_sessions_reap_and_evict(tmp_path):
    from dvah.webapi.sessions import SessionManager
    expiring = SessionManager(base=tmp_path / "a", isolated=True, ttl=0)
    s1 = expiring.create("DVAH-001")["session_id"]
    expiring.create("DVAH-002")  # reap runs → the ttl=0 session s1 is expired and dropped
    with pytest.raises(KeyError):
        expiring.path(s1)

    capped = SessionManager(base=tmp_path / "b", isolated=True, max_sessions=1)
    capped.create("DVAH-001")
    capped.create("DVAH-002")  # over cap → evict oldest
    assert len(capped._challenge) <= 1


@pytest.mark.unit
def test_sessions_bad_id_and_unknown_records(tmp_path):
    from dvah.webapi.sessions import SessionManager
    mgr = SessionManager(base=tmp_path, isolated=True)
    with pytest.raises(KeyError):
        mgr._session_root("not-hex")          # SID regex reject
    mgr.record_hint("f" * 32, 0)               # unknown id → meta None → no-op
    mgr.record_run("f" * 32, {"tests": []})    # unknown id → meta None → no-op


@pytest.mark.unit
def test_sessions_path_after_dir_removed(tmp_path):
    import shutil
    from dvah.webapi.sessions import SessionManager
    mgr = SessionManager(base=tmp_path, isolated=True)
    sid = mgr.create("DVAH-001")["session_id"]
    shutil.rmtree(mgr._dirs[sid])   # the workspace vanishes underneath us
    with pytest.raises(KeyError):
        mgr.path(sid)               # session known but dir missing → KeyError


# ---------------- catalog / invariants edges ----------------
@pytest.mark.unit
def test_catalog_missing_dir_returns_empty(tmp_path, monkeypatch):
    from dvah.scenarios import catalog
    monkeypatch.setattr(catalog, "CHALLENGES_DIR", tmp_path / "does-not-exist")
    catalog._catalog.cache_clear()
    assert catalog._catalog() == {}
    catalog._catalog.cache_clear()


@pytest.mark.unit
def test_invariants_missing_doc(monkeypatch, tmp_path):
    from dvah.webapi import invariants
    invariants.invariant_statements.cache_clear()
    monkeypatch.setattr(invariants, "_DOCS", tmp_path / "nope.md")
    assert invariants.invariant_statements() == {}
    invariants.invariant_statements.cache_clear()
