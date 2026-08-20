"""Resources layer — agent-facing read-only knowledge (the reference "Resource" primitive).

The ``Resource`` data model lives in ``dvah.models.resource``; parsing/registry behavior is in
``dvah.artifacts.resource_yaml``. This package is the domain home that re-exports both so the
tree reads as the reference architecture (Tools + Resources under an Agent).
"""

from ..artifacts.resource_yaml import load_resources
from ..models.resource import Resource

__all__ = ["Resource", "load_resources"]
