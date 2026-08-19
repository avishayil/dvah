"""ExternalHarness — a tiny self-contained mock implementing ``HarnessAdapter``.

It has NO dependency on DVAH's harness internals: it stands in for a foreign runtime
(LangGraph, CrewAI, an MCP server) reached through a thin shim. It is deliberately
correct on most invariants but WRONG on INV-01 (authorizes once, then executes the rest)
and INV-11 (approval ignores the tool digest) — so the battery visibly discriminates.

To write a real adapter, implement these methods against your runtime's authorization,
delegation, approval, context-assembly, memory, and budget primitives — the battery
supplies the scenarios and holds the assertions.
"""

from __future__ import annotations

from ..models.capability import CapabilitySet
from .adapter import ActionDescriptor, AdapterDecision, CompiledView, MemoryItem, RunOutcome


def _leaves(scripts: dict, task: str, seen: frozenset = frozenset()) -> list[tuple[str, str]]:
    """Flatten a plan into leaf (namespace, action) tool steps, expanding delegations."""
    if task in seen:
        return []
    out: list[tuple[str, str]] = []
    for step in scripts.get(task, []):
        ns, action = step["namespace"], step["action"]
        if (ns, action) == ("agent", "delegate"):
            out += _leaves(scripts, step["parameters"]["subplan_task_id"], seen | {task})
        else:
            out.append((ns, action))
    return out


class ExternalHarness:
    name = "external"

    def run_plan(self, caps, scripts, task, max_actions) -> RunOutcome:
        leaves = _leaves(scripts, task)
        # BUG (INV-01): authorize only the first step, then execute the rest anyway.
        authorized = {"h0"} if leaves else set()
        executed = []
        for i, _ in enumerate(leaves):
            if len(executed) >= max_actions:  # shared budget IS enforced (INV-06-budget ok)
                break
            executed.append(f"h{i}")
        return RunOutcome(
            executed_hashes=tuple(executed),
            authorized_hashes=frozenset(authorized),
            executed_count=len(executed),
            provenance_records=len(executed),
        )

    def derive_child(self, requested, parent, policy) -> CapabilitySet:
        return requested.intersect(parent).intersect(policy)

    def _bind(self, a: ActionDescriptor) -> str:
        # BUG (INV-11): binding omits the tool digest.
        return f"{a.actor}|{a.namespace}|{a.action}|{a.resource}|{sorted(a.parameters.items())}"

    def approve(self, action: ActionDescriptor):
        return self._bind(action)

    def validate(self, action: ActionDescriptor, grant) -> bool:
        return grant == self._bind(action)

    def compile_context(self, purpose, observations, secrets=()) -> CompiledView:
        parts = [purpose]
        for obs in observations:
            blob = repr(obs.get("content", {}))
            for s in secrets:  # correct: redact secret values
                blob = blob.replace(s, "***")
            parts.append(blob)
        return CompiledView(has_untrusted_instruction=False, text_blob=" ".join(parts))

    def authorize(self, caps, namespace, action, resource, revoked=frozenset()) -> AdapterDecision:
        if (namespace, action) in revoked:
            return AdapterDecision(allow=False, invariant="INV-09")
        if not caps.permits(namespace, action):
            return AdapterDecision(allow=False, invariant="INV-13")
        return AdapterDecision(allow=True)

    def authorize_attribution(self, principal_user, root_principal, chain, actor_agent) -> AdapterDecision:
        # correct: attribution must actually connect principal → chain → actor
        if root_principal != principal_user or not chain or chain[-1] != actor_agent:
            return AdapterDecision(allow=False, invariant="INV-08")
        return AdapterDecision(allow=True)

    def skill_grant(self, approved, requested, manifest_digest, pinned_digest) -> CapabilitySet:
        return requested.intersect(approved)

    def recall_memory(self, tenant) -> tuple[MemoryItem, ...]:
        return (MemoryItem(tenant=tenant, source="note", is_instruction=False),)

    def budget_used_racing(self, limit, concurrent) -> int:
        return min(concurrent, limit)  # atomic

    def external_tool_trust(self, declared_trust: str) -> str:
        return "untrusted_data"  # the reference mock also contains the boundary (INV-14)
