"""Backward-compatibility shim: ``dvah.services.memory`` → ``dvah.services.world_state``.

The world stores were renamed to ``world_state`` (they are the simulated external world the
agent acts on, not agent memory — see ``dvah/memory/``). Existing imports keep working here;
migrated off in the final phase, then removed.
"""

from .world_state import FileStore, GithubStore

__all__ = ["FileStore", "GithubStore"]
