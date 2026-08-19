"""Tiny pytest plugin: write a JSON per-test report to ``$DVAH_REPORT``.

Loaded by the runner via ``-p dvah.webapi._pytest_report``. Keeps the runner's result
parsing robust instead of scraping ``-q`` text output. Also records, per test, the
invariant id it covers (from ``@pytest.mark.invariant("INV-0X")``) so the runner can
report a per-invariant board, and emits an entry on collection errors so a broken edit
shows an error instead of "0 tests".
"""

from __future__ import annotations

import json
import os

from ..testing import register_markers

_PATH = os.environ.get("DVAH_REPORT")
_MARKERS = ("functional", "exploit", "invariant", "adversarial")
_results: dict[str, dict] = {}
_inv_by_node: dict[str, str] = {}


def pytest_configure(config):  # noqa: D401 - pytest hook
    """Register DVAH markers so sandboxed runs (no pyproject rootdir) don't warn."""
    register_markers(config)


def pytest_runtest_setup(item):  # noqa: D401 - pytest hook
    """Capture the invariant id declared by ``@pytest.mark.invariant("INV-0X")``."""
    marker = item.get_closest_marker("invariant")
    if marker is not None:
        inv = marker.kwargs.get("inv") or (marker.args[0] if marker.args else None)
        if inv:
            _inv_by_node[item.nodeid] = str(inv)


def pytest_runtest_logreport(report):  # noqa: D401 - pytest hook
    entry = _results.setdefault(
        report.nodeid,
        {"name": report.nodeid, "outcome": "passed", "marker": None, "invariant": None, "message": ""},
    )
    for marker in _MARKERS:
        if marker in report.keywords:
            entry["marker"] = marker
    if report.nodeid in _inv_by_node:
        entry["invariant"] = _inv_by_node[report.nodeid]
    if report.failed:
        entry["outcome"] = "error" if report.when in ("setup", "teardown") else "failed"
        if report.longrepr:
            entry["message"] = str(report.longrepr)[-800:]
    elif report.skipped and report.when == "setup" and entry["outcome"] == "passed":
        entry["outcome"] = "skipped"


def pytest_collectreport(report):  # noqa: D401 - pytest hook
    """Surface collection failures (e.g. a syntax error in edited code) as an error."""
    if report.failed:
        node = report.nodeid or "collection"
        _results[f"collect::{node}"] = {
            "name": node or "collection",
            "outcome": "error",
            "marker": None,
            "invariant": None,
            "message": str(report.longrepr)[-800:],
        }


def pytest_sessionfinish(session, exitstatus):  # noqa: D401 - pytest hook
    if _PATH:
        with open(_PATH, "w") as fh:
            json.dump(
                {"tests": list(_results.values()), "exitstatus": int(exitstatus)}, fh
            )
