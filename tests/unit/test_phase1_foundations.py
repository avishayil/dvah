"""Unit tests for the Phase-1 shared foundations (INV-07/09/10/11/12)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from dvah.harness.context import RunContext
from dvah.harness.resolver import build_envelope
from dvah.models.capability import Capability, CapabilitySet
from dvah.models.envelope import Intent
from dvah.models.identity import Actor, DelegationChain, Principal
from dvah.models.operation import Operation
from dvah.models.provenance import TrustLevel
from dvah.models.runtime import Constraints, RuntimeContext, SkillRef
from dvah.models.skill import SkillManifest
from dvah.mutation.broken import RacyBudgetTracker
from dvah.mutation.engine import run
from dvah.mutation.flags import FLAG_TO_INV, MutationFlags
from dvah.security.budget import BuiltinBudgetTracker
from dvah.security.decision import Denied
from dvah.security.revocation import AuthorityLease, RevocationRegistry
from dvah.security.skills import BuiltinSkillLoader
from dvah.services.memory_store import BuiltinMemoryProvider, MemoryStore

pytestmark = pytest.mark.unit


def _cap(n, a):
    return Capability(namespace=n, action=a)


# --- INV-07 skill loader ----------------------------------------------------
def test_skill_loader_attenuates_to_approved_and_flags_expansion():
    approved = (_cap("github", "issue.read"),)
    upgraded = SkillManifest(
        name="s",
        digest="d1",
        permissions=(_cap("github", "issue.read"), _cap("github", "repository.delete")),
    )
    res = BuiltinSkillLoader().load(upgraded, approved, pinned_digest="d1")
    assert res.granted.permits("github", "issue.read")
    assert not res.granted.permits("github", "repository.delete")
    assert res.requires_reapproval


def test_skill_loader_grants_nothing_on_digest_mismatch():
    res = BuiltinSkillLoader().load(
        SkillManifest(name="s", digest="d2", permissions=(_cap("github", "issue.read"),)),
        (_cap("github", "issue.read"),),
        pinned_digest="d1",
    )
    assert not res.trusted and res.granted.caps == frozenset()


# --- INV-09 revocation ------------------------------------------------------
def test_revocation_registry_flags_actions_and_principals():
    reg = RevocationRegistry(revoked_actions={("files", "delete")})
    env = SimpleNamespace(
        operation=SimpleNamespace(namespace="files", action="delete"),
        principal=SimpleNamespace(user="alice"),
    )
    ok = SimpleNamespace(
        operation=SimpleNamespace(namespace="files", action="read"),
        principal=SimpleNamespace(user="alice"),
    )
    assert reg.is_revoked(env) and not reg.is_revoked(ok)
    reg.revoke_principal("mallory")
    ok.principal.user = "mallory"
    assert reg.is_revoked(ok)


def test_authority_lease_expiry():
    lease = AuthorityLease(issued="2026-01-01T00:00:00Z", expires="2026-01-01T01:00:00Z")
    assert lease.valid_at("2026-01-01T00:30:00Z")
    assert not lease.valid_at("2026-01-01T02:00:00Z")


# --- INV-10 memory ----------------------------------------------------------
def test_memory_is_tenant_scoped_and_informational():
    store = MemoryStore(
        {
            "acme": [{"source": "note-acme", "content": {"x": 1}}],
            "evil": [{"source": "note-evil", "content": {}}],
        }
    )
    items = BuiltinMemoryProvider(store).recall("acme", "2026-01-01T00:00:00Z")
    assert {i["source"] for i in items} == {"note-acme"}
    assert all(i["tenant"] == "acme" for i in items)
    assert all(i["trust"] == TrustLevel.MEMORY for i in items)


# --- INV-11 tool-digest binding --------------------------------------------
def _ctx_with_skill(digest: str) -> RunContext:
    return RunContext(
        principal=Principal(user="a", tenant="t"),
        actor=Actor(agent_id="ag", instance_id="i"),
        delegation=DelegationChain(root_principal="a", chain=("ag",), depth=0),
        intent=Intent(task_id="t", purpose="p"),
        capabilities=CapabilitySet(caps=frozenset()),
        constraints=Constraints(),
        runtime=RuntimeContext(model="m", skill=SkillRef(name="s", digest=digest)),
    )


def test_action_hash_binds_tool_digest():
    op = Operation(namespace="github", action="issue.comment", resource="r")
    h1 = build_envelope(_ctx_with_skill("d1"), op).action_hash
    h2 = build_envelope(_ctx_with_skill("d2"), op).action_hash
    assert h1 != h2  # a changed tool digest changes the action identity


# --- INV-12 atomicity -------------------------------------------------------
def test_atomic_budget_denies_second_charge():
    t = BuiltinBudgetTracker(limit=1)
    t.charge(None)
    with pytest.raises(Denied):
        t.charge(None)


def test_racy_tracker_slips_past_the_limit():
    t = RacyBudgetTracker(limit=1)
    a, b = t.check(), t.check()  # both pass before either commits
    if a:
        t.commit()
    if b:
        t.commit()
    assert t.used == 2  # the race defeats the limit of 1


# --- mutation coverage ------------------------------------------------------
def test_mutation_clean_all_twelve_hold():
    result = run(MutationFlags())
    assert result.total == 15  # INV-01..14 (INV-06 split instr/budget; INV-08 attribution)
    assert result.holding == result.total


@pytest.mark.parametrize(
    "flag", ["skill_upgrade", "revocation_check", "memory_scope", "tool_digest", "atomicity"]
)
def test_each_new_flag_breaks_only_its_invariant(flag):
    result = run(MutationFlags(**{flag: True}))
    assert result.broken == [FLAG_TO_INV[flag]]
