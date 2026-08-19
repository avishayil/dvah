"""MutationFlags — one togglable "invariant defeat" per security invariant.

The mutation engine turns a hidden subset of these on and asks how many invariants
still hold. Each flag maps to the invariant it defeats and the config slot it swaps.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class MutationFlags:
    execution_authz: bool = False          # INV-01
    delegation_attenuation: bool = False   # INV-02
    approval_binding: bool = False         # INV-03
    secret_redaction: bool = False         # INV-04
    provenance_propagation: bool = False   # INV-05
    instruction_separation: bool = False   # INV-06 (data/instruction)
    budget_sharing: bool = False           # INV-06 (budget)
    tool_vs_operation: bool = False        # INV-13
    attribution_forgery: bool = False      # INV-08
    skill_upgrade: bool = False            # INV-07
    revocation_check: bool = False         # INV-09
    memory_scope: bool = False             # INV-10
    tool_digest: bool = False              # INV-11
    atomicity: bool = False                # INV-12

    def active(self) -> list[str]:
        return [f.name for f in fields(self) if getattr(self, f.name)]


#: flag name -> the invariant id it defeats (also the probe key).
FLAG_TO_INV: dict[str, str] = {
    "execution_authz": "INV-01",
    "delegation_attenuation": "INV-02",
    "approval_binding": "INV-03",
    "secret_redaction": "INV-04",
    "provenance_propagation": "INV-05",
    "instruction_separation": "INV-06-instr",
    "budget_sharing": "INV-06-budget",
    "tool_vs_operation": "INV-13",
    "attribution_forgery": "INV-08",
    "skill_upgrade": "INV-07",
    "revocation_check": "INV-09",
    "memory_scope": "INV-10",
    "tool_digest": "INV-11",
    "atomicity": "INV-12",
}

#: flag name -> the HarnessConfig slot it replaces.
FLAG_TO_SLOT: dict[str, str] = {
    "execution_authz": "executor",
    "delegation_attenuation": "capabilities",
    "approval_binding": "approvals",
    "secret_redaction": "secrets",
    "provenance_propagation": "provenance",
    "instruction_separation": "context_compiler",
    "budget_sharing": "budget",
    "tool_vs_operation": "policy",
}

ALL_FLAGS: tuple[str, ...] = tuple(FLAG_TO_INV.keys())
