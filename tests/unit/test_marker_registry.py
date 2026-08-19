"""The marker registry registers every DVAH marker on a pytest config."""

from __future__ import annotations

import pytest

from dvah.testing import MARKERS, register_markers

pytestmark = pytest.mark.unit


class _FakeConfig:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str]] = []

    def addinivalue_line(self, name: str, line: str) -> None:
        self.lines.append((name, line))


def test_registers_all_markers():
    cfg = _FakeConfig()
    register_markers(cfg)
    registered = {line.split(":", 1)[0] for name, line in cfg.lines if name == "markers"}
    assert registered == set(MARKERS)


def test_expected_markers_present():
    for m in ("functional", "exploit", "invariant", "adversarial", "unit", "integration", "e2e"):
        assert m in MARKERS
