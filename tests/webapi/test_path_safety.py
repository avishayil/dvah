"""Path-injection barriers: challenge ids and session ids can never escape their roots.

CodeQL flagged ``py/path-injection`` on paths derived from the request-supplied
``challenge_id``/``session_id``. These tests pin the barriers: strict id validation plus
a resolved-containment assertion, so a traversal attempt is rejected before any FS access
while well-formed ids keep working.
"""

from __future__ import annotations

import pytest

from dvah.scenarios import catalog
from dvah.webapi.sessions import SessionManager

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "bad",
    ["../../etc", "DVAH-001/../..", "../secrets", "a/b", "DVAH-001/..", "", "."],
)
def test_resolve_challenge_rejects_traversal(bad):
    with pytest.raises(LookupError):
        catalog.resolve_challenge(bad)


def test_resolve_challenge_accepts_valid_id():
    # A real challenge id still resolves to a directory inside challenges/.
    d = catalog.resolve_challenge("DVAH-001")
    assert d.is_dir()
    assert d.is_relative_to(catalog.challenges_dir().resolve())


def test_resolve_challenge_rejects_unknown_wellformed_id():
    # A syntactically-valid id that names no real challenge must miss the catalog lookup
    # (the barrier is a trusted dict lookup, not merely id-shape validation).
    for missing in ["DVAH-999", "DVAH-999-nope", "NOPE-1"]:
        with pytest.raises(LookupError):
            catalog.resolve_challenge(missing)


def test_validate_challenge_id():
    assert catalog.validate_challenge_id("DVAH-001-plan-time-authorization")
    for bad in ["../x", "a/b", "a.b", "a b", ""]:
        with pytest.raises(LookupError):
            catalog.validate_challenge_id(bad)


@pytest.mark.parametrize(
    "bad",
    ["../../etc", "abc", "g" * 32, "0123456789abcdef", "aa/bb", "", "../" + "a" * 30],
)
def test_session_path_rejects_malformed_id(tmp_path, bad):
    mgr = SessionManager(base=tmp_path)
    with pytest.raises(KeyError):
        mgr.path(bad)


def test_session_roundtrip_with_valid_id(tmp_path):
    mgr = SessionManager(base=tmp_path)
    created = mgr.create("DVAH-001")
    sid = created["session_id"]
    root = mgr.path(sid)
    assert root.is_dir()
    assert root.is_relative_to(tmp_path.resolve())
    assert created["editable_files"], "expected at least one editable vulnerable file"
