"""Out-of-process grader: keeps the learner's execution environment and the grader's
hidden material (tests + reference solution) in separate trust domains.

In ``isolated`` (assessment/CTF) mode the learner session holds only ``vulnerable/``;
grading assembles a throwaway workspace from the *pristine* challenge tests plus the
code under test, and the reference ``solution/`` is only ever present for explicit
``--solution`` runs — so it never coexists with learner-controlled code.

The RPC path (:func:`grade_rpc`) goes one step further: the learner's code runs in a
separate ``AdapterServer`` process whose workspace has NO ``tests/`` and NO ``solution/``,
and the grader drives the invariant battery in-process — the fullest learner/grader split.
"""

from .assembly import assemble_server_workspace, assemble_workspace
from .grader import grade, grade_rpc

__all__ = ["assemble_workspace", "assemble_server_workspace", "grade", "grade_rpc"]
