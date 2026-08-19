"""Canonical pytest marker registry.

This is the single source of truth for DVAH's custom markers. It is registered
programmatically (via ``register_markers``) from the root ``conftest.py`` and from the
``dvah.webapi._pytest_report`` plugin, so markers are known no matter what pytest picks
as its rootdir — including the sandboxed runner, which executes a copied challenge
workspace that has no ``pyproject.toml``. ``pyproject.toml`` mirrors this list for
repo-rooted CI runs (it cannot import Python).
"""

from __future__ import annotations

MARKERS: dict[str, str] = {
    "unit": "isolated single-module tests",
    "integration": "multi-component tests through the loader/harness",
    "e2e": "end-to-end over real HTTP services (manual only, excluded from CI)",
    "functional": "legitimate tasks must still work",
    "exploit": "the known attack must fail to violate the invariant",
    "invariant": "property test over generated actions",
    "adversarial": "hidden mutations that defeat challenge-specific patches",
}


def register_markers(config) -> None:
    """Register all DVAH markers on a pytest ``config`` (idempotent per run)."""
    for name, description in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {description}")
