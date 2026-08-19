"""The per-invariant board maps each declared invariant to its own covering tests."""

from __future__ import annotations

import pytest

from dvah.webapi.runner import _invariant_board

pytestmark = pytest.mark.unit


def _scenario(tmp_path, invariants):
    (tmp_path / "scenario.yaml").write_text(
        "id: X\ninvariants: [%s]\n" % ", ".join(invariants)
    )
    return tmp_path


def test_two_invariants_report_independently(tmp_path):
    d = _scenario(tmp_path, ["INV-A", "INV-B"])
    tests = [
        {"marker": "invariant", "invariant": "INV-A", "outcome": "passed"},
        {"marker": "invariant", "invariant": "INV-B", "outcome": "failed"},
    ]
    board = _invariant_board(d, tests)
    per = {p["id"]: p["holds"] for p in board["per"]}
    assert per == {"INV-A": True, "INV-B": False}
    assert board == {"holding": 1, "total": 2, "per": board["per"]}


def test_untagged_invariant_test_covers_all(tmp_path):
    d = _scenario(tmp_path, ["INV-A", "INV-B"])
    tests = [{"marker": "invariant", "invariant": None, "outcome": "failed"}]
    board = _invariant_board(d, tests)
    assert all(not p["holds"] for p in board["per"])


def test_single_invariant_backcompat(tmp_path):
    d = _scenario(tmp_path, ["INV-01"])
    tests = [{"marker": "invariant", "invariant": "INV-01", "outcome": "passed"}]
    assert _invariant_board(d, tests) == {
        "holding": 1,
        "total": 1,
        "per": [{"id": "INV-01", "holds": True}],
    }


def test_no_invariant_tests_means_not_held(tmp_path):
    d = _scenario(tmp_path, ["INV-01"])
    assert _invariant_board(d, [])["per"] == [{"id": "INV-01", "holds": False}]
