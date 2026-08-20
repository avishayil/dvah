"""Backward-compatibility shim: ``dvah.services.memory_store`` → ``dvah.memory.store``.

Agent memory moved to the top-level ``dvah/memory/`` package (the reference-architecture
Memory/State layer). Existing imports keep working here; migrated off in the final phase.
"""

from ..memory.store import BuiltinMemoryProvider, MemoryProvider, MemoryStore

__all__ = ["MemoryStore", "MemoryProvider", "BuiltinMemoryProvider"]
