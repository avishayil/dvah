"""Ephemeral per-user workspaces.

Two grader modes (env ``DVAH_GRADER``):

- ``inprocess`` (default, self-study): a session is a full copy of the challenge dir —
  including ``tests/`` and ``solution/`` — and the suite runs in the session itself. Fast
  to iterate, but NOT isolation: ``solution/`` is on disk (only hidden from the file API),
  so learner-executed code could read it. Intended for local single-user self-study.
- ``isolated`` (assessment/CTF): the session holds ONLY ``vulnerable/`` (+ ``environment/``
  + ``scenario.yaml``). It contains neither ``tests/`` nor ``solution/``. Grading happens
  out of band in a throwaway workspace (see ``dvah.grading``) where the reference solution
  never coexists with learner-controlled code.

Only files under the session's ``vulnerable/`` are writable, and path resolution is
guarded against traversal.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path

from ..scenarios import catalog

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

#: Session ids are server-generated ``uuid4().hex`` — 32 lowercase hex chars. Validating
#: against this (no separators/traversal) is the taint barrier for ``py/path-injection``
#: on any path built from a request-supplied session id.
_SID_RE = re.compile(r"^[0-9a-f]{32}$")

# Ephemeral-session limits (local dev defaults; override via env).
_SESSION_TTL = int(os.environ.get("DVAH_SESSION_TTL", "3600"))  # seconds
_MAX_SESSIONS = int(os.environ.get("DVAH_MAX_SESSIONS", "200"))

# "inprocess" (self-study, full copy) | "isolated" (assessment, vulnerable-only session).
GRADER_MODE = os.environ.get("DVAH_GRADER", "inprocess")

# What an isolated learner session is allowed to contain — never tests/ or solution/.
# ``skills``/``agents`` hold the file-based artifacts (SKILL.md, agents/*.md); they are
# safe to copy (no secret material) and let the isolated session's loader parse them.
_LEARNER_ONLY = ("vulnerable", "environment", "scenario.yaml", "skills", "agents")

# A self-contained conftest for the session: binds the ``loaded`` fixture to THIS
# challenge copy, so the sandboxed pytest run needs no ``--challenge`` option (avoiding
# a double option-registration collision with the repo's root conftest).
_SESSION_CONFTEST = '''\
import pytest
from pathlib import Path
from dvah.scenarios.loader import load_challenge


@pytest.fixture
def loaded():
    return load_challenge(Path(__file__).parent, use_solution=False)
'''


def _editable_files(root: Path) -> list[dict]:
    vuln = root / "vulnerable"
    return [
        {"path": f"vulnerable/{p.name}", "contents": p.read_text(), "writable": True}
        for p in sorted(vuln.glob("*.py"))
        if p.name != "__init__.py"
    ]


# Environment files opened READ-ONLY in the editor: the "world" the runtime runs against.
# users/agents/plans are surfaced verbatim; resources.yaml is values-withheld (keys only)
# so secret material never leaves the server — mirrors ``catalog._resource_summary``.
_ENV_VERBATIM = ("users", "agents", "plans")
_RESOURCES_HEADER = "# values withheld — secret material stays server-side\n"


def _resources_keys_only(text: str) -> str:
    """Render resources.yaml as namespace → key names only (no values)."""
    import yaml

    data = yaml.safe_load(text) or {}
    summary = {
        namespace: (list(entries.keys()) if isinstance(entries, dict) else entries)
        for namespace, entries in data.items()
    }
    return _RESOURCES_HEADER + yaml.safe_dump(summary, sort_keys=False)


def _readonly_files(root: Path) -> list[dict]:
    """The environment files, as read-only editor tabs (see ``_ENV_VERBATIM``)."""
    env = root / "environment"
    out: list[dict] = []
    for name in _ENV_VERBATIM:
        p = env / f"{name}.yaml"
        if p.exists():
            out.append(
                {"path": f"environment/{name}.yaml", "contents": p.read_text(), "writable": False}
            )
    res = env / "resources.yaml"
    if res.exists():
        out.append(
            {
                "path": "environment/resources.yaml",
                "contents": _resources_keys_only(res.read_text()),
                "writable": False,
            }
        )
    out.extend(_artifact_files(root))
    return out


def _artifact_files(root: Path) -> list[dict]:
    """The file-based artifacts (skills/**/SKILL.md, skills/registry.yaml, agents/*.md,
    environment/tools.yaml) as read-only "world" tabs — the real-world shapes a learner
    should recognize. Opt-in per lab; absent files simply contribute nothing."""
    out: list[dict] = []
    skills = root / "skills"
    if skills.is_dir():
        registry = skills / "registry.yaml"
        if registry.exists():
            out.append({"path": "skills/registry.yaml",
                        "contents": registry.read_text(), "writable": False})
        for md in sorted(skills.glob("*/SKILL.md")):
            rel = md.relative_to(root).as_posix()
            out.append({"path": rel, "contents": md.read_text(), "writable": False})
    for md in sorted((root / "agents").glob("*.md")):
        rel = md.relative_to(root).as_posix()
        out.append({"path": rel, "contents": md.read_text(), "writable": False})
    tools = root / "environment" / "tools.yaml"
    if tools.exists():
        out.append({"path": "environment/tools.yaml",
                    "contents": tools.read_text(), "writable": False})
    return out


def _tasks(root: Path) -> list[str]:
    plans = root / "environment" / "plans.yaml"
    if not plans.exists():
        return []
    import yaml

    return list((yaml.safe_load(plans.read_text()) or {}).keys())


class SessionManager:
    """Creates, serves, and cleans up ephemeral challenge workspaces."""

    def __init__(self, base: str | Path | None = None, ttl: int = _SESSION_TTL,
                 max_sessions: int = _MAX_SESSIONS, isolated: bool | None = None) -> None:
        self._base = Path(base) if base else Path(tempfile.mkdtemp(prefix="dvah-sessions-"))
        self._base.mkdir(parents=True, exist_ok=True)
        # Isolated = assessment mode: sessions never contain tests/ or solution/.
        # "rpc" is isolated too (vulnerable-only session; graded across a process boundary).
        self._isolated = (GRADER_MODE in ("isolated", "rpc")) if isolated is None else isolated
        self._lock = threading.RLock()
        self._challenge: dict[str, str] = {}  # session_id -> challenge_id
        # session_id -> its dir. The dir is built once from a server-generated uuid (never
        # from request input), so returning THIS value — rather than re-joining the caller's
        # session id — is the ``py/path-injection`` barrier: request ids only index the dict.
        self._dirs: dict[str, Path] = {}
        self._created: dict[str, float] = {}  # session_id -> creation time
        self._meta: dict[str, dict] = {}  # session_id -> {mode, events, start, first_green, ...}
        self._ttl = ttl
        self._max = max_sessions

    def _reap_locked(self) -> None:
        """Drop expired sessions, then evict oldest if over the cap. Caller holds lock."""
        now = time.time()
        for sid in [s for s, t in self._created.items() if now - t > self._ttl]:
            self._remove_locked(sid)
        while len(self._challenge) >= self._max and self._created:
            oldest = min(self._created, key=self._created.get)
            self._remove_locked(oldest)

    def _session_root(self, session_id: str) -> Path:
        """Resolve a session id to its dir, validating the id + asserting containment.

        Barrier for ``py/path-injection``: a request-supplied id that isn't a 32-char
        hex token, or that escapes the sessions base, is rejected before any FS access.
        """
        if not _SID_RE.fullmatch(session_id):
            raise KeyError(session_id)
        root = (self._base / session_id).resolve()
        if not root.is_relative_to(self._base.resolve()):
            raise KeyError(session_id)
        return root

    def _remove_locked(self, session_id: str) -> None:
        # Remove via the stored (server-generated) dir — never a path re-joined from the id.
        target = self._dirs.pop(session_id, None)
        if target is not None:
            shutil.rmtree(target, ignore_errors=True)
        self._challenge.pop(session_id, None)
        self._created.pop(session_id, None)
        self._meta.pop(session_id, None)

    def _materialize(self, source: Path, dest: Path) -> None:
        """Copy the challenge into a session dir. Isolated mode copies only the
        learner-visible parts (no tests/, no solution/); inprocess copies everything."""
        if not self._isolated:
            shutil.copytree(source, dest)
            return
        dest.mkdir(parents=True, exist_ok=True)
        for name in _LEARNER_ONLY:
            src = source / name
            if not src.exists():
                continue
            if src.is_dir():
                shutil.copytree(src, dest / name)
            else:
                shutil.copy2(src, dest / name)

    def create(self, challenge_id: str, mode: str = "learn") -> dict:
        source = catalog.resolve_challenge(challenge_id)  # validates id + asserts containment
        session_id = uuid.uuid4().hex
        dest = self._session_root(session_id)  # validated + containment-checked
        self._materialize(source, dest)
        (dest / "conftest.py").write_text(_SESSION_CONFTEST)
        with self._lock:
            self._reap_locked()
            self._challenge[session_id] = challenge_id
            self._dirs[session_id] = dest  # dest derives from the uuid, not request input
            self._created[session_id] = time.time()
            self._meta[session_id] = {
                "mode": "ctf" if mode == "ctf" else "learn",
                "events": [],
                "start": time.monotonic(),
                "first_green": None,  # seconds to first all-green run
                "hints_revealed": 0,
                "runs": 0,
                "last_failing": [],  # test names from the most recent run
                "last_trace": {},  # most recent trace summary
            }
        return {
            "session_id": session_id,
            "editable_files": _editable_files(dest),
            "readonly_files": _readonly_files(dest),
            "tasks": _tasks(dest),
        }

    def path(self, session_id: str) -> Path:
        with self._lock:
            # Source the dir from the stored map (trusted, uuid-derived) — the request id
            # only looks it up, so no path is built from request input here.
            root = self._dirs.get(session_id)
            if root is None:
                raise KeyError(session_id)
            expired = (
                session_id in self._created
                and time.time() - self._created[session_id] > self._ttl
            )
            if expired:
                self._remove_locked(session_id)
                raise KeyError(session_id)
            if session_id not in self._challenge or not root.is_dir():
                raise KeyError(session_id)
        return root

    def challenge_id(self, session_id: str) -> str:
        return self._challenge[session_id]

    @property
    def isolated(self) -> bool:
        """True when sessions are assessment-isolated (graded out of band)."""
        return self._isolated

    def code_dir(self, session_id: str) -> Path:
        """The learner's editable ``vulnerable/`` dir — the code under test for grading."""
        return self.path(session_id) / "vulnerable"

    def files(self, session_id: str) -> list[dict]:
        return _editable_files(self.path(session_id))

    def readonly_files(self, session_id: str) -> list[dict]:
        """Environment files served read-only (never writable)."""
        return _readonly_files(self.path(session_id))

    def tasks(self, session_id: str) -> list[str]:
        return _tasks(self.path(session_id))

    def resolve_writable(self, session_id: str, rel_path: str) -> Path:
        """Resolve a client path to a file under the session's ``vulnerable/`` dir."""
        root = self.path(session_id).resolve()
        vuln = (root / "vulnerable").resolve()
        target = (root / rel_path).resolve()
        # must stay under vulnerable/ and be a .py file (no traversal, no __init__ clobber)
        if not str(target).startswith(str(vuln) + "/") or target.suffix != ".py":
            raise PermissionError(f"path not writable: {rel_path!r}")
        return target

    def write_file(self, session_id: str, rel_path: str, contents: str) -> None:
        target = self.resolve_writable(session_id, rel_path)
        target.write_text(contents)

    def reset(self, session_id: str) -> list[dict]:
        source = catalog.resolve_challenge(self.challenge_id(session_id))
        dest = self.path(session_id)
        shutil.rmtree(dest / "vulnerable")
        shutil.copytree(source / "vulnerable", dest / "vulnerable")
        return _editable_files(dest)

    def cleanup(self, session_id: str) -> None:
        with self._lock:
            self._remove_locked(session_id)

    # --- mode + progress --------------------------------------------------
    def mode(self, session_id: str) -> str:
        """The session's declared mode ("learn"/"ctf"); "learn" if unknown."""
        with self._lock:
            return self._meta.get(session_id, {}).get("mode", "learn")

    def record_hint(self, session_id: str, tier: int) -> None:
        with self._lock:
            meta = self._meta.get(session_id)
            if meta is None:
                return
            meta["hints_revealed"] += 1
            meta["events"].append({"kind": "hint_revealed", "tier": tier})

    def record_run(self, session_id: str, result: dict) -> None:
        """Log a run's per-marker outcomes + invariant board; stamp first all-green."""
        tests = result.get("tests", [])
        failing = [t["name"] for t in tests if t.get("outcome") != "passed"]
        inv = result.get("invariants", {})
        all_green = bool(tests) and not failing and inv.get("holding") == inv.get("total")
        with self._lock:
            meta = self._meta.get(session_id)
            if meta is None:
                return
            meta["runs"] += 1
            meta["last_failing"] = failing
            meta["events"].append({
                "kind": "run",
                "passed": len(tests) - len(failing),
                "failed": len(failing),
                "invariants": inv,
            })
            if all_green and meta["first_green"] is None:
                meta["first_green"] = time.monotonic() - meta["start"]

    def record_trace(self, session_id: str, summary: dict) -> None:
        with self._lock:
            meta = self._meta.get(session_id)
            if meta is not None:
                meta["last_trace"] = summary

    def last_failing(self, session_id: str) -> list[str]:
        with self._lock:
            return list(self._meta.get(session_id, {}).get("last_failing", []))

    def last_trace_summary(self, session_id: str) -> dict:
        with self._lock:
            return dict(self._meta.get(session_id, {}).get("last_trace", {}))

    def progress(self, session_id: str) -> dict:
        with self._lock:
            meta = self._meta.get(session_id, {})
            return {
                "mode": meta.get("mode", "learn"),
                "runs": meta.get("runs", 0),
                "hints_revealed": meta.get("hints_revealed", 0),
                "time_to_first_all_green_s": meta.get("first_green"),
                "events": list(meta.get("events", [])),
            }
