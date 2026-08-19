"""Root pytest configuration shared by all challenge test suites.

``--challenge`` points at a challenge directory; the ``loaded`` fixture builds a
runnable Harness from it. ``--solution`` swaps in the reference fix so the grader can
confirm the intended architecture passes. Run one challenge per session (challenge
packages share the names ``vulnerable``/``solution``).
"""

from __future__ import annotations

import pytest

from dvah.scenarios.loader import load_challenge
from dvah.testing import register_markers


def pytest_configure(config) -> None:
    # Register markers here too so repo-rooted / `dvah test` runs never warn, even if the
    # pyproject config isn't the chosen inifile.
    register_markers(config)


def pytest_addoption(parser) -> None:
    parser.addoption("--challenge", action="store", default=None,
                     help="path to the challenge directory under test")
    parser.addoption("--solution", action="store_true", default=False,
                     help="load the reference solution instead of the vulnerable code")


@pytest.fixture
def loaded(request):
    challenge = request.config.getoption("--challenge")
    if challenge is None:
        pytest.skip("no --challenge provided")
    return load_challenge(challenge, use_solution=request.config.getoption("--solution"))
