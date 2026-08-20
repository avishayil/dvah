import pytest

from dvah.artifacts.agent_md import load_agent
from dvah.models.capability import Capability

AGENT = """---
name: skill-runner
description: Root incident-triage agent.
model: balanced
tools: [github.issue.read]
capabilities:
  - {namespace: github, action: issue.read}
delegation: {allowed: true, max_depth: 2}
skills: [github-investigator]
---
You triage incidents. Load only approved skills.
"""


@pytest.mark.unit
def test_agent_md_maps_all_frontmatter_fields(tmp_path):
    path = tmp_path / "skill-runner.md"
    path.write_text(AGENT)

    agent = load_agent(path)

    assert agent.agent_id == "skill-runner"
    assert agent.name == "skill-runner"
    assert agent.description == "Root incident-triage agent."
    assert agent.model == "balanced"
    assert agent.tools == ("github.issue.read",)
    assert agent.capabilities == (Capability(namespace="github", action="issue.read"),)
    assert agent.delegation.allowed is True
    assert agent.delegation.max_depth == 2
    assert agent.skills == ("github-investigator",)
    assert agent.instructions == "You triage incidents. Load only approved skills."


@pytest.mark.unit
def test_agent_id_defaults_to_filename_stem(tmp_path):
    path = tmp_path / "coordinator.md"
    path.write_text("---\nname: Coordinator\n---\nbody")
    agent = load_agent(path)
    assert agent.agent_id == "coordinator"
    assert agent.delegation.allowed is False


@pytest.mark.unit
def test_allowed_tools_alias(tmp_path):
    path = tmp_path / "a.md"
    path.write_text("---\nname: a\nallowed-tools: [files.read]\n---\nbody")
    assert load_agent(path).tools == ("files.read",)


@pytest.mark.unit
def test_malformed_frontmatter_raises_with_path(tmp_path):
    path = tmp_path / "a.md"
    path.write_text("---\nname: a\nno closing fence")
    with pytest.raises(ValueError, match=str(path)):
        load_agent(path)


@pytest.mark.unit
def test_non_mapping_delegation_raises(tmp_path):
    path = tmp_path / "a.md"
    path.write_text("---\nname: a\ndelegation: not-a-mapping\n---\nbody")
    with pytest.raises(ValueError, match="'delegation' must be a mapping"):
        load_agent(path)
