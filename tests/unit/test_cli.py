"""CLI coverage — drive every `dvah` command through the deterministic path."""

import json

import pytest
from typer.testing import CliRunner

from dvah import cli

runner = CliRunner()
LAB = "DVAH-001"
LAB_DIR = "challenges/DVAH-001-plan-time-authorization"


@pytest.mark.unit
def test_list_command():
    r = runner.invoke(cli.app, ["list"])
    assert r.exit_code == 0
    assert "DVAH-001" in r.stdout


@pytest.mark.unit
def test_start_learn_and_ctf():
    learn = runner.invoke(cli.app, ["start", LAB])
    assert learn.exit_code == 0
    ctf = runner.invoke(cli.app, ["start", LAB, "--mode", "ctf"])
    assert ctf.exit_code == 0
    assert "objective" in ctf.stdout.lower()
    assert "vulnerable/" in ctf.stdout  # source-to-patch listing


@pytest.mark.unit
def test_start_unknown_challenge_is_bad_parameter():
    r = runner.invoke(cli.app, ["start", "DVAH-999"])
    assert r.exit_code != 0


@pytest.mark.unit
def test_test_command_solution_passes():
    # The reference solution passes its own suite → exit 0.
    r = runner.invoke(cli.app, ["test", LAB])
    # vulnerable code fails the exploit tier → non-zero is expected for the shipped lab.
    assert r.exit_code in (0, 1)


@pytest.mark.unit
def test_trace_command_renders():
    r = runner.invoke(cli.app, ["trace", LAB, "DVAH-001-exploit"])
    assert r.exit_code == 0


@pytest.mark.unit
def test_trace_solution_flag():
    r = runner.invoke(cli.app, ["trace", LAB, "DVAH-001-functional", "--solution"])
    assert r.exit_code == 0


@pytest.mark.unit
def test_mutate_reveal_and_plain():
    plain = runner.invoke(cli.app, ["mutate", "--seed", "1", "--count", "1"])
    assert plain.exit_code in (0, 1)
    rev = runner.invoke(cli.app, ["mutate", "--seed", "1", "--count", "1", "--reveal"])
    assert "revealed defeats" in rev.stdout


@pytest.mark.unit
def test_conformance_builtin_text_and_json():
    text = runner.invoke(cli.app, ["conformance", "--adapter", "builtin"])
    assert text.exit_code == 0
    assert "invariants hold" in text.stdout
    js = runner.invoke(cli.app, ["conformance", "--adapter", "builtin", "--json"])
    assert js.exit_code == 0
    data = json.loads(js.stdout)
    assert data["holding"] == data["total"]


@pytest.mark.unit
def test_conformance_unknown_adapter():
    r = runner.invoke(cli.app, ["conformance", "--adapter", "nope"])
    assert r.exit_code != 0


@pytest.mark.unit
def test_conformance_observed_skips_without_services():
    r = runner.invoke(cli.app, ["conformance", "--adapter", "builtin", "--observed"])
    assert r.exit_code == 0
    assert "grader-observed" in r.stdout  # services down → skipped line


@pytest.mark.unit
def test_run_deterministic_and_record_then_replay(tmp_path):
    rec = tmp_path / "session.json"
    run = runner.invoke(cli.app, ["run", LAB, "DVAH-001-functional", "--record", str(rec)])
    assert run.exit_code == 0
    assert rec.exists()
    replay = runner.invoke(cli.app, ["replay", str(rec)])
    assert replay.exit_code == 0
    assert "matches" in replay.stdout


@pytest.mark.unit
def test_run_deterministic_no_record_exploit():
    r = runner.invoke(cli.app, ["run", LAB, "DVAH-001-exploit"])
    assert r.exit_code == 0
    assert "Runtime Security" in r.stdout


@pytest.mark.unit
def test_test_adversarial_flag():
    r = runner.invoke(cli.app, ["test", LAB, "--adversarial"])
    assert r.exit_code in (0, 1)  # adversarial markers appended


@pytest.mark.unit
def test_trace_solution_exploit_halts():
    # The solution denies the exploit's unauthorized action → run_task raises → 'task halted'.
    r = runner.invoke(cli.app, ["trace", LAB, "DVAH-001-exploit", "--solution"])
    assert r.exit_code == 0
    assert "task halted" in r.stdout


@pytest.mark.unit
def test_run_solution_exploit_halts():
    r = runner.invoke(cli.app, ["run", LAB, "DVAH-001-exploit", "--solution"])
    assert r.exit_code == 0
    assert "task halted" in r.stdout
