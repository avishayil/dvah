"""Agent memory (INV-10) — tenant-scoped, informational recall, never a privileged instruction.

Distinct from world state (``dvah/services/world_state.py``: FileStore/GithubStore the agent
acts on via tools). This is the reference-architecture Memory/State layer.
"""

from .store import BuiltinMemoryProvider, MemoryProvider, MemoryStore

__all__ = ["MemoryStore", "MemoryProvider", "BuiltinMemoryProvider"]
