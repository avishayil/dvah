"""FIXED provenance tracker: preserves every tag (INV-05)."""

from __future__ import annotations

from dvah.security.provenance import BuiltinProvenanceTracker


class FixedProvenanceTracker(BuiltinProvenanceTracker):
    pass
