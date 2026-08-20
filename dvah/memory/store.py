"""Agent memory (INV-10): tenant-scoped and informational.

Memory notes are recalled into the model context as DATA tagged ``TrustLevel.MEMORY`` —
never cross-tenant, never promoted to the instruction channel. A vulnerable provider
that leaks other tenants' notes (or treats memory as an instruction) is exactly the
cross-tenant memory-poisoning failure.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.provenance import TrustLevel


class MemoryStore:
    """In-memory notes keyed by tenant. Seedable and resettable for deterministic labs."""

    def __init__(self, seed: dict[str, list[dict]] | None = None) -> None:
        self._by_tenant: dict[str, list[dict]] = {
            t: list(notes) for t, notes in (seed or {}).items()
        }

    def reset(self, seed: dict[str, list[dict]] | None = None) -> None:
        self._by_tenant = {t: list(notes) for t, notes in (seed or {}).items()}

    def add(self, tenant: str, source: str, content: dict) -> None:
        self._by_tenant.setdefault(tenant, []).append({"source": source, "content": content})

    def notes(self, tenant: str) -> list[dict]:
        return list(self._by_tenant.get(tenant, []))


@runtime_checkable
class MemoryProvider(Protocol):
    def recall(self, tenant: str, timestamp: str) -> tuple[dict, ...]: ...


class BuiltinMemoryProvider:
    """Correct provider: tenant-scoped, informational (MEMORY trust), never instruction."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self._store = store or MemoryStore()

    def recall(self, tenant: str, timestamp: str) -> tuple[dict, ...]:
        return tuple(
            {
                "trust": TrustLevel.MEMORY,
                "tenant": tenant,
                "source": note["source"],
                "content": note["content"],
                "timestamp": timestamp,
            }
            for note in self._store.notes(tenant)
        )
