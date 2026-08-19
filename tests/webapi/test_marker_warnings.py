"""A sandboxed lab run must not flood stdout with PytestUnknownMarkWarning.

Regression test: markers were only in the root pyproject, so the runner (which executes
a copied session workspace with no pyproject) warned once per marker.
"""

from __future__ import annotations

import pytest

from dvah.webapi.runner import SubprocessRunner
from dvah.webapi.sessions import SessionManager

pytestmark = pytest.mark.integration


def test_runner_stdout_has_no_unknown_mark_warnings():
    mgr = SessionManager()
    created = mgr.create("DVAH-002")
    sid = created["session_id"]
    try:
        result = SubprocessRunner().run(
            mgr.path(sid), ["functional", "exploit", "invariant", "adversarial"]
        )
    finally:
        mgr.cleanup(sid)
    assert "PytestUnknownMarkWarning" not in result["stdout"]
    # sanity: the suite actually ran (markers resolved, tests collected)
    assert result["tests"]
