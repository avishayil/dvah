"""Phase 2: the loader parses resources/workflows/prompts for every lab (additive)."""

import pytest

from dvah.models.prompt import PromptStack
from dvah.models.resource import Resource
from dvah.models.workflow import Workflow
from dvah.scenarios.catalog import scenario_dirs
from dvah.scenarios.loader import load_challenge

LAB_DIRS = scenario_dirs()
LAB_IDS = [d.name for d in LAB_DIRS]


@pytest.mark.integration
@pytest.mark.parametrize("challenge_dir", LAB_DIRS, ids=LAB_IDS)
def test_loader_exposes_reference_artifacts(challenge_dir):
    loaded = load_challenge(challenge_dir)
    assert all(isinstance(r, Resource) for r in loaded.resources.values())
    assert all(isinstance(w, Workflow) for w in loaded.workflows.values())
    assert all(isinstance(p, PromptStack) for p in loaded.prompts.values())
    # every declared agent gets a (possibly empty) prompt stack
    assert set(loaded.prompts) == set(loaded.agent_defs)


@pytest.mark.integration
def test_workflows_mirror_plans_tasks():
    loaded = load_challenge("challenges/DVAH-001-plan-time-authorization")
    assert "DVAH-001-exploit" in loaded.workflows
    wf = loaded.workflows["DVAH-001-exploit"]
    assert wf.steps and wf.steps[0].namespace == "files"


@pytest.mark.integration
def test_resources_derived_from_world_seed():
    loaded = load_challenge("challenges/DVAH-001-plan-time-authorization")
    # DVAH-001 seeds files -> file:// knowledge resources (advisory view)
    assert any(rid.startswith("file://") for rid in loaded.resources)


@pytest.mark.integration
def test_prompt_stack_includes_agent_instructions_when_authored():
    loaded = load_challenge("challenges/DVAH-009-skill-upgrade")
    stack = loaded.prompts["skill-runner"]
    assert "triage" in stack.render().lower()
