"""VULNERABLE policy: authorize once, reuse the decision forever (INV-09).

The bug: the first resolved action's decision is cached and returned for every later
action, so authority is never re-validated — a revocation issued mid-run is ignored.
"""

from __future__ import annotations

from dvah.security.policy import BuiltinPolicy


class CachingPolicy:
    def __init__(self) -> None:
        self._base = BuiltinPolicy()
        self._cached = None

    def authorize(self, envelope):
        if self._cached is None:  # BUG: decide once, then trust it for the whole run
            self._cached = self._base.authorize(envelope)
        return self._cached
