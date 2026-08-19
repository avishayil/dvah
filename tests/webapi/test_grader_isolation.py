"""Phase 7 — out-of-process grader: learner and grader trust domains are separated.

In isolated (assessment) mode the learner session contains only ``vulnerable/`` — never
``tests/`` or ``solution/`` — and grading runs in a throwaway workspace where the
reference solution never coexists with learner-controlled code. These tests use the
``SubprocessRunner`` directly (CI has no Docker); container isolation is exercised
manually via ``DVAH_RUNNER=docker``.
"""

from __future__ import annotations

import pytest

from dvah.grading import assemble_workspace, grade
from dvah.scenarios import catalog
from dvah.webapi.runner import SubprocessRunner
from dvah.webapi.sessions import SessionManager

pytestmark = pytest.mark.integration

_RUNNER = SubprocessRunner()

# A correct fix for DVAH-001 (class name must stay VulnerableExecutor — the override
# targets that symbol); routes every resolved action through the broker gate.
_FIXED_EXECUTOR = '''
_DELEGATE = ("agent", "delegate")
_REFLECT = ("agent", "reflect")


class VulnerableExecutor:
    def execute_plan(self, harness, ctx, steps):
        results = []
        for step in steps:
            if (step.namespace, step.action) == _DELEGATE:
                results.extend(harness.delegate(ctx, step))
                continue
            if (step.namespace, step.action) == _REFLECT:
                results.extend(harness.reflect(ctx, step))
                continue
            outcome = harness.broker.run_step(ctx, step)
            ctx = outcome.ctx
            results.append(outcome.result)
        harness.last_ctx = ctx
        return results
'''


def _mgr(tmp_path, *, isolated):
    return SessionManager(base=tmp_path / ("iso" if isolated else "std"), isolated=isolated)


def test_isolated_session_omits_tests_and_solution(tmp_path):
    m = _mgr(tmp_path, isolated=True)
    root = m.path(m.create("DVAH-001")["session_id"])
    assert (root / "vulnerable").is_dir()
    assert (root / "scenario.yaml").exists()
    assert not (root / "solution").exists()  # never in the learner's tree
    assert not (root / "tests").exists()


def test_selfstudy_session_keeps_full_copy(tmp_path):
    m = _mgr(tmp_path, isolated=False)
    root = m.path(m.create("DVAH-001")["session_id"])
    assert (root / "solution").is_dir() and (root / "tests").is_dir()


def test_learner_grader_workspace_never_contains_solution(tmp_path):
    source = catalog.resolve_challenge("DVAH-001")
    ws = assemble_workspace(source, tmp_path / "ws", code_dir=None, use_solution=False)
    assert (ws / "vulnerable").is_dir() and (ws / "tests").is_dir()
    assert not (ws / "solution").exists()  # solution absent even while learner code runs


def test_isolated_grade_vulnerable_red_reference_green(tmp_path):
    m = _mgr(tmp_path, isolated=True)
    sid = m.create("DVAH-001")["session_id"]
    red = grade("DVAH-001", code_dir=m.code_dir(sid),
                markers=["exploit", "invariant"], runner=_RUNNER)
    assert any(t["outcome"] == "failed" for t in red["tests"])  # bug present → red

    green = grade("DVAH-001", code_dir=None,
                  markers=["functional", "exploit", "invariant"],
                  use_solution=True, runner=_RUNNER)
    assert green["tests"] and all(t["outcome"] == "passed" for t in green["tests"]), green["stdout"]


def test_isolated_patched_submission_goes_green(tmp_path):
    m = _mgr(tmp_path, isolated=True)
    sid = m.create("DVAH-001")["session_id"]
    m.write_file(sid, "vulnerable/executor.py", _FIXED_EXECUTOR)
    body = grade("DVAH-001", code_dir=m.code_dir(sid),
                 markers=["functional", "exploit", "invariant"], runner=_RUNNER)
    assert body["tests"] and all(t["outcome"] == "passed" for t in body["tests"]), body["stdout"]


def test_hostile_patch_finds_no_solution_in_isolated_session(tmp_path):
    """A learner patch that tries to read ../solution finds nothing: it's not on disk."""
    m = _mgr(tmp_path, isolated=True)
    root = m.path(m.create("DVAH-001")["session_id"])
    assert list(root.glob("**/solution")) == []
    assert list(root.glob("**/test_*.py")) == []
