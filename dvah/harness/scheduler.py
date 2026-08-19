"""Deterministic scheduler seam (INV-12): security decisions must be atomic.

Real runtimes break under concurrency: a check-then-act on a shared limit lets two
in-flight agents both pass before either commits. To keep DVAH CI-stable we model the
race deterministically — no real threads — via an explicit interleaving of callables.
The default ``SequentialScheduler`` runs steps in order and is used by every existing
lab unchanged.
"""

from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

Op = Callable[[], None]


@runtime_checkable
class Scheduler(Protocol):
    def run(self, ops: list[Op]) -> None: ...


class SequentialScheduler:
    """Runs operations in the given order (the default, race-free path)."""

    def run(self, ops: list[Op]) -> None:
        for op in ops:
            op()


class InterleavingScheduler:
    """Runs operations in an explicit, caller-supplied order — used to force a race.

    ``order`` is a list of indices into ``ops`` (e.g. ``[0, 1, 0, 1]`` to interleave two
    two-phase operations). Deterministic and thread-free.
    """

    def __init__(self, order: list[int]) -> None:
        self._order = order

    def run(self, ops: list[Op]) -> None:
        for i in self._order:
            ops[i]()
