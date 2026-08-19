"""FIXED capability resolver: attenuate to the intersection.

child = requested ∩ parent ∩ policy (INV-02). A child can never exceed its parent.
"""

from __future__ import annotations


class FixedCapabilityResolver:
    def derive_child(self, requested, parent, policy):
        return requested.intersect(parent).intersect(policy)
