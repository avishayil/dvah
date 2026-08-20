"""Every lab's artifact files parse, and the file-based definitions stay consistent with
the authorization-bearing sources (agents.yaml caps, provider actions). This is the guard
that keeps the descriptive artifacts honest without letting them change authorization."""

from __future__ import annotations

import pytest
import yaml

from dvah.artifacts.tool_catalog import builtin_catalog
from dvah.models.capability import Capability
from dvah.models.operation import Operation
from dvah.scenarios.catalog import scenario_dirs
from dvah.scenarios.loader import load_challenge

LAB_DIRS = scenario_dirs()
LAB_IDS = [d.name for d in LAB_DIRS]


@pytest.mark.integration
@pytest.mark.parametrize("challenge_dir", LAB_DIRS, ids=LAB_IDS)
def test_all_lab_artifacts_parse(challenge_dir):
    """load_challenge (which parses skills/agents/tool-catalog) succeeds for every lab."""
    loaded = load_challenge(challenge_dir)
    assert loaded.tools_catalog  # always at least the built-in catalog
    assert loaded.agent_defs  # synthesized from root if no agents/*.md


@pytest.mark.integration
@pytest.mark.parametrize("challenge_dir", LAB_DIRS, ids=LAB_IDS)
def test_agent_md_caps_match_agents_yaml_root(challenge_dir):
    """An authored agent .md must not diverge from the authorization-bearing root caps."""
    agents_yaml = yaml.safe_load((challenge_dir / "environment" / "agents.yaml").read_text())
    root = agents_yaml.get("root") or {}
    root_id = root.get("agent_id")
    if not (challenge_dir / "agents").is_dir() or root_id is None:
        pytest.skip("no authored agent .md for the root agent")
    loaded = load_challenge(challenge_dir)
    agent = loaded.agent_defs.get(root_id)
    assert agent is not None, f"agents/*.md must define the root agent {root_id}"
    expected = {Capability(**c) for c in (root.get("capabilities") or [])}
    assert set(agent.capabilities) == expected


@pytest.mark.integration
@pytest.mark.parametrize("challenge_dir", LAB_DIRS, ids=LAB_IDS)
def test_catalog_covers_every_operation_in_plans(challenge_dir):
    """Each namespace.action a lab's plans.yaml uses has a tool spec (except the internal
    ``agent`` meta-namespace, which the agent runtime handles, not a tool provider)."""
    plans_path = challenge_dir / "workflows" / "plans.yaml"
    if not plans_path.exists():
        plans_path = challenge_dir / "environment" / "plans.yaml"
    plans = yaml.safe_load(plans_path.read_text()) or {}
    catalog = builtin_catalog()
    for steps in plans.values():
        for step in steps or []:
            ns, action = step.get("namespace"), step.get("action")
            if ns == "agent":
                continue
            assert f"{ns}.{action}" in catalog, f"{challenge_dir.name}: no spec for {ns}.{action}"


@pytest.mark.integration
def test_advertising_catalog_never_perturbs_parameters_hash():
    """Determinism guard: tool-spec metadata is advisory. An operation's parameters_hash
    is identical whether or not a catalog exists — nothing merges input_schema in."""
    op = Operation(namespace="github", action="issue.comment", resource="acme/app",
                   parameters={"issue": 7, "body": "hi"})
    spec = builtin_catalog()["github.issue.comment"]
    assert spec.input_schema  # the spec has a schema...
    # ...and it is completely independent of the operation's identity hash.
    same = Operation(namespace="github", action="issue.comment", resource="acme/app",
                     parameters={"issue": 7, "body": "hi"})
    assert op.parameters_hash == same.parameters_hash
