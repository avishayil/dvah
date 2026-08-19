"""Grade a submission in an isolated, out-of-process workspace.

Grades the learner's current code — or the reference solution — by assembling a fresh
workspace (:func:`assemble_workspace`) and running it through the same sandboxed runner
the web UI uses (``SubprocessRunner`` / ``DockerRunner``). The learner session is never
the execution root, so it need not (and must not) contain the hidden tests or solution.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from ..scenarios import catalog
from .assembly import assemble_workspace


def grade(
    challenge_id: str,
    *,
    code_dir: Path | None,
    markers: list[str],
    use_solution: bool = False,
    runner=None,
    task_id: str | None = None,
) -> dict:
    """Assemble → run → collect. Returns the same result shape as the runner."""
    # Lazy import avoids any webapi import cycle at package load.
    from ..webapi import runner as _runner

    source = catalog.resolve_challenge(challenge_id)
    runner = runner or _runner.get_runner()
    workspace = Path(tempfile.mkdtemp(prefix="dvah-grader-"))
    try:
        assemble_workspace(source, workspace, code_dir=code_dir, use_solution=use_solution)
        return runner.run(workspace, markers, task_id)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def grade_rpc(challenge_id: str, *, code_dir: Path | None, use_solution: bool = False) -> dict:
    """Grade the invariant battery ACROSS a process boundary (full learner/grader split).

    The learner's code runs in a separate ``AdapterServer`` process whose workspace contains
    NO ``tests/`` and NO ``solution/``; the grader (this process) drives ``run_battery`` and
    holds all assertions. Returns a per-invariant verdict dict (the security-oracle result);
    the per-tier pytest grading (functional/exploit/…) still uses :func:`grade`.
    """
    from ..conformance.battery import run_battery
    from .assembly import assemble_server_workspace
    from .rpc import RpcAdapter

    source = catalog.resolve_challenge(challenge_id)
    workspace = Path(tempfile.mkdtemp(prefix="dvah-rpc-"))
    try:
        assemble_server_workspace(source, workspace, code_dir=code_dir, use_solution=use_solution)
        adapter = RpcAdapter(workspace, use_solution=use_solution)
        try:
            run = run_battery(adapter)
        finally:
            adapter.close()
        return {
            "mode": "rpc",
            "passed": run.passed,
            "holding": run.holding,
            "total": run.total,
            "invariants": run.holds,
            "broken": run.broken,
        }
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
