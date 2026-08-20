"""VULNERABLE provenance tracker: merge silently drops the tag (INV-05)."""

from __future__ import annotations

from dvah.guardrails.provenance import BuiltinProvenanceTracker


class VulnerableProvenanceTracker(BuiltinProvenanceTracker):
    def merge(self, record, tag):
        return record  # BUG: provenance is discarded
