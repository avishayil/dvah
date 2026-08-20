"""Shared frontmatter-field coercions for the artifact parsers."""

from __future__ import annotations

from ..models.capability import Capability


def as_str_tuple(value) -> tuple[str, ...]:
    """Coerce a frontmatter list, comma-string, or scalar into a tuple of strings.

    Accepts ``[a, b]``, ``"a, b"``, ``"a"`` or ``None`` — the shapes ``allowed-tools`` /
    ``skills`` appear in real frontmatter.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return tuple(str(v) for v in value)


def as_capabilities(value) -> tuple[Capability, ...]:
    """Coerce a list of ``{namespace, action}`` mappings into ``Capability`` objects."""
    return tuple(Capability(**c) for c in (value or []))
