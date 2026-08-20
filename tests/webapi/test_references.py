"""The briefing exposes the source of the harness modules a lab's code imports."""

from __future__ import annotations

import pytest

from dvah.webapi import catalog

pytestmark = pytest.mark.unit


def test_briefing_includes_referenced_harness_modules():
    b = catalog.briefing("DVAH-001-plan-time-authorization")
    refs = {r["module"]: r["contents"] for r in b["references"]}
    # DVAH-001's vulnerable executor imports these — learners must be able to read them.
    assert "dvah.harness.resolver" in refs
    assert "dvah.guardrails.decision" in refs
    assert "def resolve_operation" in refs["dvah.harness.resolver"]
    assert all(r["contents"] for r in b["references"])


def test_references_skip_non_dvah_imports():
    b = catalog.briefing("DVAH-001-plan-time-authorization")
    assert all(r["module"].startswith("dvah") for r in b["references"])
