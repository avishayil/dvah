"""Integration tests for `dvah conformance` and its relationship to `dvah mutate`."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from dvah.cli import app
from dvah.conformance.battery import INVARIANTS
from dvah.mutation.engine import PROBES

pytestmark = pytest.mark.integration

runner = CliRunner()


def test_conformance_builtin_passes():
    result = runner.invoke(app, ["conformance", "--adapter", "builtin"])
    assert result.exit_code == 0
    assert "15 / 15 invariants hold" in result.stdout


def test_conformance_external_reports_failures_and_exits_nonzero():
    result = runner.invoke(app, ["conformance", "--adapter", "external"])
    assert result.exit_code == 1
    assert "INV-01" in result.stdout and "INV-11" in result.stdout
    assert "13 / 15" in result.stdout


def test_conformance_json_output():
    result = runner.invoke(app, ["conformance", "--adapter", "builtin", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["holding"] == payload["total"] == 15
    assert {r["invariant"] for r in payload["results"]} == set(INVARIANTS)


def test_unknown_adapter_rejected():
    result = runner.invoke(app, ["conformance", "--adapter", "nope"])
    assert result.exit_code != 0


def test_conformance_and_mutation_share_the_invariant_set():
    # The mutation battery and the conformance battery cover the same invariant keys.
    assert set(PROBES.keys()) == set(INVARIANTS)
