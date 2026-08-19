"""The catalog exposes learner-facing curriculum metadata, ordered beginner→advanced."""

from __future__ import annotations

import pytest

from dvah.webapi import catalog

pytestmark = pytest.mark.unit


def test_list_exposes_metadata_and_is_ordered():
    data = catalog.list_challenges()["challenges"]
    assert len(data) >= 13
    for key in ("order", "difficulty", "estimated_minutes", "teaches"):
        assert key in data[0]
    orders = [c["order"] for c in data]
    assert orders == sorted(orders)  # beginner → advanced
    assert data[0]["id"] == "DVAH-001"


def test_briefing_exposes_metadata():
    b = catalog.briefing("DVAH-001")
    assert b["order"] == 1
    assert b["teaches"]
    assert b["difficulty"] == "easy"
