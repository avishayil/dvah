"""Sandboxed execution of user-edited lab code.

``SubprocessRunner`` (default) runs the lab's pytest suite in a child process group with
a wall-clock timeout, an output byte cap, and — on Linux — ``resource`` rlimits. macOS
degrades to timeout + rlimits and is DEV-ONLY (not safe for hosting untrusted users).
``DockerRunner`` (``DVAH_RUNNER=docker``) runs the same command in a locked-down
container (``--network none``, read-only rootfs, non-root, cpu/mem/pids caps).

Results are collected by the ``dvah.webapi._pytest_report`` plugin (JSON), not scraped.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import yaml

DEFAULT_TIMEOUT = int(os.environ.get("DVAH_RUN_TIMEOUT", "60"))
_OUTPUT_CAP = 200_000  # bytes of captured stdout kept
_MAX_CONCURRENT = int(os.environ.get("DVAH_RUN_CONCURRENCY", "2"))
_slots = threading.Semaphore(_MAX_CONCURRENT)


def _declared_invariants(session_dir: Path) -> list[str]:
    spec = yaml.safe_load((session_dir / "scenario.yaml").read_text())
    return list(spec.get("invariants", []))


def _invariant_board(session_dir: Path, tests: list[dict]) -> dict:
    """Map each declared invariant to the pass/fail of the tests that cover it.

    A test covers invariant X if it is tagged X (``@pytest.mark.invariant("X")``); an
    untagged invariant test covers ALL declared invariants (back-compat). An invariant
    holds iff it has at least one covering invariant-test and none of them failed —
    identical behaviour to before for single-invariant labs, but now per-invariant.
    """
    declared = _declared_invariants(session_dir)
    invariant_tests = [t for t in tests if t.get("marker") == "invariant"]
    per = []
    for inv in declared:
        covering = [t for t in invariant_tests if t.get("invariant") in (None, inv)]
        holds = bool(covering) and all(t["outcome"] == "passed" for t in covering)
        per.append({"id": inv, "holds": holds})
    return {"holding": sum(1 for p in per if p["holds"]), "total": len(per), "per": per}


# Only these env vars are forwarded to the untrusted-code subprocess — credentials
# (ANTHROPIC_API_KEY, OPENAI_API_KEY, AWS_*, etc.) are intentionally withheld so learner
# code cannot read them, while the interpreter/venv still resolves.
_SAFE_ENV = (
    "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TEMP", "TMP",
    "VIRTUAL_ENV", "PYTHONPATH", "PYTHONHOME", "SYSTEMROOT", "TERM",
)


def _child_env(report_path: Path) -> dict:
    env = {k: os.environ[k] for k in _SAFE_ENV if k in os.environ}
    env["DVAH_REPORT"] = str(report_path)
    env["PYTHONUNBUFFERED"] = "1"
    return env


def _rlimits() -> None:  # pragma: no cover - exercised only in child process
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    except Exception:
        pass


class SubprocessRunner:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def _command(self, session_dir: Path, markers: list[str], report: Path) -> list[str]:
        marker_expr = " or ".join(markers) if markers else "functional or exploit or invariant"
        return [
            sys.executable, "-m", "pytest", "evals",
            "-m", marker_expr,
            "-p", "dvah.webapi._pytest_report", "-p", "no:cacheprovider",
            "--tb=line", "-q",
        ]

    def run(self, session_dir: Path, markers: list[str], task_id: str | None = None) -> dict:
        session_dir = Path(session_dir)
        with _slots:
            with tempfile.NamedTemporaryFile("r", suffix=".json", delete=False) as tmp:
                report_path = Path(tmp.name)
            env = _child_env(report_path)
            popen_kwargs = dict(
                cwd=str(session_dir), env=env, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, start_new_session=True,
            )
            if sys.platform.startswith("linux"):
                popen_kwargs["preexec_fn"] = _rlimits  # pragma: no cover - POSIX rlimits (platform-specific)
            proc = subprocess.Popen(self._command(session_dir, markers, report_path), **popen_kwargs)
            try:
                stdout, _ = proc.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                stdout, _ = proc.communicate()
                stdout = (stdout or "") + "\n[dvah] run killed: timeout exceeded"
            exit_code = proc.returncode
            tests = self._read_report(report_path)
            report_path.unlink(missing_ok=True)
        return {
            "tests": tests,
            "invariants": _invariant_board(session_dir, tests),
            "stdout": (stdout or "")[:_OUTPUT_CAP],
            "exit_code": exit_code if exit_code is not None else -1,
        }

    @staticmethod
    def _read_report(path: Path) -> list[dict]:
        try:
            return json.loads(path.read_text()).get("tests", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []


class DockerRunner(SubprocessRunner):  # pragma: no cover - container runtime; deploy-only, needs Docker
    """Run the suite inside a locked-down container (untrusted-code hosting)."""

    IMAGE = os.environ.get("DVAH_RUNNER_IMAGE", "dvah-runner:latest")

    def run(self, session_dir: Path, markers: list[str], task_id: str | None = None) -> dict:
        session_dir = Path(session_dir)
        marker_expr = " or ".join(markers) if markers else "functional or exploit or invariant"
        with _slots:
            report_name = "report.json"
            cmd = [
                "docker", "run", "--rm", "--network", "none", "--read-only",
                "--user", "65534:65534", "--memory", "512m", "--cpus", "1",
                "--pids-limit", "128",
                "--tmpfs", "/tmp:rw,size=64m",
                "-v", f"{session_dir}:/work:rw", "-w", "/work",
                "-e", f"DVAH_REPORT=/work/{report_name}",
                self.IMAGE,
                "python", "-m", "pytest", "tests", "-m", marker_expr,
                "-p", "dvah.webapi._pytest_report",
                "-p", "no:cacheprovider", "--tb=line", "-q",
            ]
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout + 30
            )
            tests = self._read_report(session_dir / report_name)
            (session_dir / report_name).unlink(missing_ok=True)
        return {
            "tests": tests,
            "invariants": _invariant_board(session_dir, tests),
            "stdout": (proc.stdout + proc.stderr)[:_OUTPUT_CAP],
            "exit_code": proc.returncode,
        }


def get_runner() -> SubprocessRunner:
    if os.environ.get("DVAH_RUNNER") == "docker":
        return DockerRunner()  # pragma: no cover - selected only when DVAH_RUNNER=docker
    return SubprocessRunner()
