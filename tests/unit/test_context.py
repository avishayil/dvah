import pytest
from dataclasses import FrozenInstanceError

from dvah.models.approval import ApprovalGrant
from dvah.models.capability import Capability, CapabilitySet
from dvah.models.provenance import ProvenanceRecord, ProvenanceTag, TrustLevel

pytestmark = pytest.mark.unit


def test_next_action_id_encodes_depth_and_count(make_ctx):
    ctx = make_ctx()
    assert ctx.next_action_id() == "act-d0-0"
    assert ctx.tick().next_action_id() == "act-d0-1"


def test_tick_is_immutable(make_ctx):
    ctx = make_ctx()
    ticked = ctx.tick()
    assert ticked.actions_used == 1
    assert ctx.actions_used == 0


def test_context_is_frozen(make_ctx):
    ctx = make_ctx()
    with pytest.raises(FrozenInstanceError):
        ctx.actions_used = 5


def test_with_provenance(make_ctx):
    ctx = make_ctx()
    rec = ProvenanceRecord().with_data(
        ProvenanceTag(source="s", trust=TrustLevel.UNTRUSTED_DATA, tenant="acme", timestamp="t"))
    assert ctx.with_provenance(rec).provenance is rec


def test_grants_and_find_grant(make_ctx):
    ctx = make_ctx()
    grant = ApprovalGrant(approval_id="a", approved_action_hash="sha256:xyz")
    ctx2 = ctx.with_grant(grant)
    assert ctx2.find_grant("sha256:xyz") is grant
    assert ctx2.find_grant("sha256:other") is None
    assert ctx.grants == ()


def test_child_resets_and_extends(make_ctx):
    caps = CapabilitySet(caps=frozenset({Capability(namespace="files", action="read")}))
    parent = make_ctx(agent_id="root").with_grant(
        ApprovalGrant(approval_id="a", approved_action_hash="h")).tick()
    child = parent.child("kid", "kid-inst", caps)
    assert child.actor.agent_id == "kid"
    assert child.delegation.chain == ("root", "kid")
    assert child.delegation.depth == 1
    assert child.capabilities is caps
    assert child.grants == ()
    assert child.actions_used == 0
