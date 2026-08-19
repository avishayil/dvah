"""Canonical hashing helpers.

Every security decision that must be stable across processes and time relies on a
deterministic serialization. ``canonical_json`` guarantees sorted keys and no
incidental whitespace so the same logical object always yields the same digest.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, compact separators, stable str fallback."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_of(obj: Any) -> str:
    """Return a namespaced sha256 digest of ``obj``'s canonical JSON form."""
    digest = hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
