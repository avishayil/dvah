"""Shared challenge catalog — one source of truth for the CLI and the web API.

Lists challenges, reads a scenario, and resolves an id (or path) to a challenge
directory. Kept dependency-light so both ``dvah.cli`` and ``dvah.webapi`` can import it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

#: Repository ``challenges/`` directory (``dvah/`` is one level below the repo root).
CHALLENGES_DIR = Path(__file__).resolve().parent.parent.parent / "challenges"

#: A safe challenge id: letters, digits, dashes only (blocks path traversal).
_ID_RE = re.compile(r"^[A-Za-z0-9-]+$")

#: The ``DVAH-001`` prefix embedded in a dir name like ``DVAH-001-plan-time-authorization``.
_PREFIX_RE = re.compile(r"^([A-Za-z]+-\d+)")


def _ensure_contained(path: Path) -> Path:
    """Resolve ``path`` and assert it stays inside ``challenges/``.

    This is the taint barrier for ``py/path-injection``: every path derived from an
    externally-supplied id/path is funnelled through here, so a resolved location that
    escapes the challenges root is rejected before any read.
    """
    resolved = path.resolve()
    root = CHALLENGES_DIR.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise LookupError(f"path escapes challenges/: {path!r}")
    return resolved


def _within_challenges(path: Path) -> bool:
    try:
        _ensure_contained(path)
        return True
    except LookupError:
        return False


def validate_challenge_id(challenge_id: str) -> str:
    """Return ``challenge_id`` if it is a safe id (no separators/traversal), else raise."""
    if not _ID_RE.fullmatch(challenge_id):
        raise LookupError(f"invalid challenge id {challenge_id!r}")
    return challenge_id


def challenges_dir() -> Path:
    return CHALLENGES_DIR


def read_scenario(challenge_dir: str | Path) -> dict:
    safe_dir = _ensure_contained(Path(challenge_dir))
    return yaml.safe_load((safe_dir / "scenario.yaml").read_text())


def iter_scenarios():
    """Yield each challenge's parsed ``scenario.yaml``, ordered by id."""
    for path in sorted(CHALLENGES_DIR.glob("*/scenario.yaml")):
        yield yaml.safe_load(path.read_text())


def scenario_dirs() -> list[Path]:
    return [p.parent for p in sorted(CHALLENGES_DIR.glob("*/scenario.yaml"))]


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Path]:
    """Map every known challenge id → its trusted directory, built from the filesystem.

    This is the ``py/path-injection`` barrier for ids: the mapping is produced entirely by
    scanning ``CHALLENGES_DIR`` (a constant derived from ``__file__``), so every value is a
    trusted ``Path``. External input is only ever used to *index* this dict — never joined
    into a path — so an id that isn't a real challenge simply misses and is rejected.

    Each challenge is keyed three ways: full dir name (``DVAH-001-...``), the ``DVAH-001``
    prefix, and the ``scenario.yaml`` ``id`` field.
    """
    mapping: dict[str, Path] = {}
    if not CHALLENGES_DIR.is_dir():
        return mapping
    for child in sorted(CHALLENGES_DIR.iterdir()):
        if not child.is_dir() or not (child / "scenario.yaml").is_file():
            continue
        mapping[child.name] = child
        prefix = _PREFIX_RE.match(child.name)
        if prefix:
            mapping.setdefault(prefix.group(1), child)
        try:
            spec = yaml.safe_load((child / "scenario.yaml").read_text())
        except (OSError, yaml.YAMLError):
            spec = None
        if isinstance(spec, dict) and isinstance(spec.get("id"), str):
            mapping.setdefault(spec["id"], child)
    return mapping


def resolve_challenge(id_or_path: str) -> Path:
    """Resolve a challenge id (``DVAH-001``) or a directory path to its trusted directory.

    Ids only *index* the filesystem-built :func:`_catalog`, and a directory path is accepted
    only if it matches a catalog entry — in both cases the returned ``Path`` comes from the
    trusted catalog, never from joining the caller's string (the ``py/path-injection`` fix).
    """
    catalog = _catalog()
    path = Path(id_or_path)
    if path.is_dir():
        # Accept a directory path only if it IS one of the known challenge dirs; return the
        # trusted catalog value (never the caller-supplied path).
        resolved = path.resolve()
        for trusted in catalog.values():
            if trusted.resolve() == resolved:
                return trusted
        raise LookupError(f"no challenge at {id_or_path!r}")
    # Id form: validate (letters/digits/dash — no separators/traversal), then look up.
    cid = validate_challenge_id(id_or_path)
    trusted = catalog.get(cid)
    if trusted is None:
        raise LookupError(f"no challenge matching {id_or_path!r}")
    return trusted
