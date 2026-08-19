"""Integration tests exercising the challenge loader end to end (solution slots)."""

import sys
from pathlib import Path

import pytest

from dvah.scenarios.loader import load_challenge

pytestmark = pytest.mark.integration

CHALLENGES = Path(__file__).resolve().parents[2] / "challenges"


@pytest.fixture(autouse=True)
def _isolate_challenge_imports():
    """Challenges share the top-level package names ``vulnerable``/``solution``.

    Loading more than one per process collides in sys.modules (a known loader
    limitation), so snapshot and restore import state around each test.
    """
    saved_path = list(sys.path)
    yield
    for name in [m for m in sys.modules if m.split(".")[0] in {"vulnerable", "solution"}]:
        del sys.modules[name]
    for entry in list(sys.path):
        if entry not in saved_path and "challenges" in entry:
            sys.path.remove(entry)


def test_load_dvah001_solution_runs_functional():
    loaded = load_challenge(CHALLENGES / "DVAH-001-plan-time-authorization", use_solution=True)
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-001-functional")
    assert results[0].ok
    assert results[0].output["contents"] == "harmless scratch data"


def test_load_dvah002_solution_runs_functional():
    loaded = load_challenge(CHALLENGES / "DVAH-002-privileged-child", use_solution=True)
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-002-functional")
    assert results[0].ok
    assert results[0].output["issues"][0]["id"] == 418


def test_loader_seeds_stores_and_builds_root_context():
    loaded = load_challenge(CHALLENGES / "DVAH-001-plan-time-authorization")
    assert loaded.files.exists("/prod/customer.db")
    assert loaded.root_ctx.principal.user == "alice"
    assert loaded.root_ctx.delegation.root_principal == "alice"


def test_loader_exposes_task_prompts_when_tasks_yaml_present():
    loaded = load_challenge(CHALLENGES / "DVAH-001-plan-time-authorization")
    # DVAH-001 ships a tasks.yaml keyed by the same task_ids as plans.yaml.
    assert "DVAH-001-exploit" in loaded.tasks
    prompt = loaded.task_prompt("DVAH-001-exploit")
    assert prompt and "authorized" in prompt.lower()
    # the root agent is surfaced as a world object (keyed by its declared agent_id)
    assert loaded.root_ctx.actor.agent_id in loaded.agents


def test_loader_derives_default_prompt_without_tasks_yaml():
    # DVAH-002 has no tasks.yaml → task_prompt falls back to a derived default.
    loaded = load_challenge(CHALLENGES / "DVAH-002-privileged-child")
    assert loaded.tasks == {}
    default = loaded.task_prompt("anything")
    assert default  # non-empty, derived from objective/title
    assert loaded.task_prompt("DVAH-002-functional") == default


def test_tasks_yaml_does_not_change_deterministic_run():
    # Adding tasks.yaml must not alter the scripted deterministic outcome.
    loaded = load_challenge(
        CHALLENGES / "DVAH-001-plan-time-authorization", use_solution=True
    )
    results = loaded.harness.run_task(loaded.root_ctx, "DVAH-001-functional")
    assert results[0].ok
    assert results[0].output["contents"] == "harmless scratch data"
