import pytest
from pydantic import ValidationError

from dvah.models.identity import Actor, DelegationChain, Principal

pytestmark = pytest.mark.unit


def test_principal_is_frozen():
    p = Principal(user="alice", tenant="acme")
    with pytest.raises(ValidationError):
        p.user = "mallory"


def test_actor_construction():
    a = Actor(agent_id="agent", instance_id="agent-1")
    assert a.agent_id == "agent"


def test_delegation_chain_extend_increments_depth_and_appends():
    chain = DelegationChain(root_principal="alice", chain=("a",), depth=0)
    child = chain.extend("b")
    assert child.chain == ("a", "b")
    assert child.depth == 1
    assert child.root_principal == "alice"
    # original is unchanged (immutability)
    assert chain.chain == ("a",)
    assert chain.depth == 0
    # extend keeps the depth == len(chain) - 1 invariant
    assert child.depth == len(child.chain) - 1


def test_delegation_chain_rejects_depth_length_mismatch():
    with pytest.raises(ValidationError):
        DelegationChain(root_principal="alice", chain=("a",), depth=5)
    with pytest.raises(ValidationError):
        DelegationChain(root_principal="alice", chain=("a", "b"), depth=0)


def test_delegation_chain_rejects_empty_chain_or_root():
    with pytest.raises(ValidationError):
        DelegationChain(root_principal="alice", chain=(), depth=0)
    with pytest.raises(ValidationError):
        DelegationChain(root_principal="", chain=("a",), depth=0)


def test_delegation_chain_model_construct_bypasses_validation():
    # forgeries must be explicit — model_construct skips the validator (used by defeats/tests)
    forged = DelegationChain.model_construct(root_principal="", chain=(), depth=99)
    assert forged.depth == 99
