"""Assemble a throwaway, isolated grader workspace.

A grader workspace is a fresh temp dir containing the *pristine* challenge tests +
environment + scenario, a session-style ``conftest.py`` binding the ``loaded`` fixture
to THIS workspace, and exactly one code overlay:

- learner grading (``use_solution=False``): the code under test is copied in as
  ``vulnerable/``; ``solution/`` is deliberately **absent**, so even though the
  learner's code executes during grading it cannot read the reference solution.
- reference run (``use_solution=True``): the pristine ``solution/`` is copied in and no
  learner-controlled code is present.

This is the trust-domain split: the solution never coexists with learner code, and the
learner's own session (see ``dvah.webapi.sessions``) contains neither tests nor solution.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# Binds the ``loaded`` fixture to THIS workspace with the right mode, so the sandboxed
# pytest run needs no ``--challenge`` option (mirrors the per-session conftest).
_CONFTEST = '''\
import pytest
from pathlib import Path
from dvah.scenarios.loader import load_challenge


@pytest.fixture
def loaded():
    return load_challenge(Path(__file__).parent, use_solution={use_solution})
'''


def assemble_workspace(
    source: Path, dest: Path, *, code_dir: Path | None, use_solution: bool
) -> Path:
    """Build a grader workspace under ``dest`` from pristine ``source``.

    ``code_dir`` overlays the learner's current ``vulnerable/`` for a learner run; when
    ``None`` the pristine ``vulnerable/`` is used. Ignored for reference runs.
    """
    source = Path(source)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source / "tests", dest / "tests")
    shutil.copytree(source / "environment", dest / "environment")
    shutil.copy2(source / "scenario.yaml", dest / "scenario.yaml")
    (dest / "conftest.py").write_text(_CONFTEST.format(use_solution=use_solution))

    if use_solution:
        # Reference run: pristine solution only, never any learner-controlled code.
        shutil.copytree(source / "solution", dest / "solution")
    else:
        # Learner run: the code under test only; solution/ is intentionally not copied.
        overlay = Path(code_dir) if code_dir else (source / "vulnerable")
        shutil.copytree(overlay, dest / "vulnerable")
    return dest


def assemble_server_workspace(
    source: Path, dest: Path, *, code_dir: Path | None, use_solution: bool
) -> Path:
    """Assemble a workspace for the RPC ``AdapterServer`` that runs the learner's code.

    Unlike :func:`assemble_workspace`, this OMITS ``tests/`` entirely — the hidden assertions
    live in the grader process (the battery), not on the learner-executed filesystem. It
    contains only the code under test (``vulnerable/`` from ``code_dir``, or ``solution/`` for
    a reference run), plus ``environment/`` + ``scenario.yaml`` the loader needs. ``solution/``
    is present ONLY for a reference run; a learner run has neither ``tests/`` nor ``solution/``.
    """
    source = Path(source)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source / "environment", dest / "environment")
    shutil.copy2(source / "scenario.yaml", dest / "scenario.yaml")

    if use_solution:
        shutil.copytree(source / "solution", dest / "solution")
    else:
        overlay = Path(code_dir) if code_dir else (source / "vulnerable")
        shutil.copytree(overlay, dest / "vulnerable")
    return dest
