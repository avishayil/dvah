import pytest

from dvah.mutation import broken
from dvah.mutation.engine import apply, choose_flags
from dvah.mutation.flags import ALL_FLAGS, FLAG_TO_INV, FLAG_TO_SLOT, MutationFlags
from dvah.security.secrets import BuiltinSecretBroker


@pytest.mark.unit
def test_flags_default_all_off():
    assert MutationFlags().active() == []


@pytest.mark.unit
def test_active_lists_only_toggled():
    assert MutationFlags(approval_binding=True).active() == ["approval_binding"]


@pytest.mark.unit
def test_flag_maps_are_complete():
    assert set(FLAG_TO_INV) == set(ALL_FLAGS)
    # Slot-swap flags (INV-01..08) are a subset; INV-07/09..12 are self-probed and
    # intentionally not in FLAG_TO_SLOT.
    assert set(FLAG_TO_SLOT) <= set(FLAG_TO_INV)
    assert len(set(FLAG_TO_INV.values())) == len(ALL_FLAGS)  # each defeats a distinct inv


@pytest.mark.unit
def test_apply_swaps_only_active_slots_without_mutating_base():
    base = {slot: f"orig-{slot}" for slot in FLAG_TO_SLOT.values()}
    base["secrets"] = BuiltinSecretBroker()
    out = apply(MutationFlags(execution_authz=True), base)
    assert isinstance(out["executor"], broken.PlanTimeExecutor)
    assert out["capabilities"] == "orig-capabilities"  # untouched slot preserved
    assert base["executor"] == "orig-executor"  # original dict not mutated


@pytest.mark.unit
def test_secret_defeat_wraps_existing_broker():
    inner = BuiltinSecretBroker(credentials={"k": "v"})
    out = apply(MutationFlags(secret_redaction=True), {"secrets": inner})
    assert isinstance(out["secrets"], broken.NoRedactSecretBroker)
    assert out["secrets"].redact_for_model(({"x": "v"},)) == ({"x": "v"},)  # no redaction


@pytest.mark.unit
def test_choose_flags_is_seed_deterministic():
    assert choose_flags(7, 3).active() == choose_flags(7, 3).active()


@pytest.mark.unit
def test_choose_flags_count_is_clamped():
    assert len(choose_flags(0, 999).active()) == len(ALL_FLAGS)
    assert choose_flags(0, 0).active() == []
