"""Backward-compatibility shim: ``dvah.security`` → ``dvah.guardrails``.

The security services were renamed to ``guardrails`` (the reference-architecture term for
this cross-cutting layer). This shim keeps existing imports —
``from dvah.security.decision import Denied``, ``from dvah.security import policy`` — working
by aliasing each guardrails submodule into ``sys.modules`` under the old path. Tests and
challenge code migrate off it in the final phase; then this package is removed.
"""

from __future__ import annotations

import importlib
import sys

_SUBMODULES = (
    "decision", "policy", "approvals", "capabilities", "budget",
    "secrets", "provenance", "revocation", "skills",
)

for _name in _SUBMODULES:
    _module = importlib.import_module(f"dvah.guardrails.{_name}")
    sys.modules[f"{__name__}.{_name}"] = _module
    globals()[_name] = _module

del importlib, sys, _name, _module
