import pytest
from pydantic import ValidationError

from dvah.models.capability import Capability, CapabilitySet
from dvah.models.identity import Actor, DelegationChain
from dvah.models.operation import Operation
from dvah.guardrails.decision import Verdict
from dvah.guardrails.policy import BuiltinPolicy

pytestmark = pytest.mark.unit


def _caps(*pairs):
    return CapabilitySet(caps=frozenset(Capability(namespace=n, action=a) for n, a in pairs))


def test_allow_when_capability_permits(make_envelope):
    env = make_envelope(
        operation=Operation(namespace="github", action="issue.read", resource="r"),
        capabilities=_caps(("github", "issue.read")),
    )
    assert BuiltinPolicy().authorize(env).verdict is Verdict.ALLOW


def test_deny_inv01_when_no_capability(make_envelope):
    env = make_envelope(
        operation=Operation(namespace="github", action="issue.read", resource="r"),
        capabilities=_caps(),
    )
    decision = BuiltinPolicy().authorize(env)
    assert decision.verdict is Verdict.DENY
    assert decision.invariant == "INV-01"


def _forge_delegation(ctx, **overrides):
    """Build a degenerate/forged delegation chain that bypasses the model validator,
    modelling a malicious or buggy caller, and splice it into a copy of ``ctx``."""
    fields = {"root_principal": ctx.delegation.root_principal,
              "chain": ctx.delegation.chain, "depth": ctx.delegation.depth}
    fields.update(overrides)
    forged = DelegationChain.model_construct(**fields)
    return ctx.__class__(**{**ctx.__dict__, "delegation": forged})


def test_envelope_rejects_structurally_invalid_attribution(make_ctx, make_envelope):
    # A chain with an empty root can't even be embedded in an ActionEnvelope — the model
    # revalidates it, so missing attribution is stopped a layer *below* the policy.
    ctx = make_ctx(capabilities=_caps(("files", "read")))
    broken = _forge_delegation(ctx, root_principal="")
    with pytest.raises(ValidationError):
        make_envelope(operation=Operation(namespace="files", action="read", resource="/x"), ctx=broken)


def test_deny_inv08_when_root_principal_mismatches(make_ctx, make_envelope):
    # attribution present but forged: root_principal claims someone other than the principal
    ctx = make_ctx(capabilities=_caps(("files", "read")), user="alice")
    broken = _forge_delegation(ctx, root_principal="mallory")
    env = make_envelope(operation=Operation(namespace="files", action="read", resource="/x"), ctx=broken)
    decision = BuiltinPolicy().authorize(env)
    assert decision.verdict is Verdict.DENY
    assert decision.invariant == "INV-08"


def test_deny_inv08_when_chain_tip_is_not_the_actor(make_ctx, make_envelope):
    # the acting agent isn't the tail of the delegation chain → not truly attributable
    ctx = make_ctx(capabilities=_caps(("files", "read")), agent_id="root-agent")
    forged = ctx.__class__(**{**ctx.__dict__, "actor": Actor(agent_id="ghost", instance_id="ghost-1")})
    env = make_envelope(operation=Operation(namespace="files", action="read", resource="/x"), ctx=forged)
    decision = BuiltinPolicy().authorize(env)
    assert decision.verdict is Verdict.DENY
    assert decision.invariant == "INV-08"


def test_needs_approval_for_approval_actions(make_envelope):
    env = make_envelope(
        operation=Operation(namespace="files", action="delete", resource="/prod"),
        capabilities=_caps(("files", "delete")),
    )
    assert BuiltinPolicy().authorize(env).verdict is Verdict.NEEDS_APPROVAL


def test_tool_vs_operation_capability_is_action_scoped(make_envelope):
    # holding issue.read must NOT permit issue.comment — operation-granular mediation
    # (upholds INV-13; the denial is tagged INV-01 complete mediation).
    env = make_envelope(
        operation=Operation(namespace="github", action="issue.comment", resource="r"),
        capabilities=_caps(("github", "issue.read")),
    )
    decision = BuiltinPolicy().authorize(env)
    assert decision.verdict is Verdict.DENY
    assert decision.invariant == "INV-01"
