"""Unit tests for the v0.3 scenario-world helpers in the loader (pure functions)."""

import pytest

from dvah.scenarios.loader import _default_prompt, _load_agents

pytestmark = pytest.mark.unit


def test_default_prompt_prefers_objective_exploit():
    spec = {"id": "DVAH-00X", "title": "T", "objective": {"exploit": "do the thing"}}
    assert _default_prompt(spec) == "do the thing"


def test_default_prompt_falls_back_to_title_then_id():
    assert _default_prompt({"id": "DVAH-00X", "title": "Only a title"}) == "Only a title"
    assert _default_prompt({"id": "DVAH-00X"}) == "DVAH-00X"
    assert _default_prompt({}) == ""


def test_load_agents_legacy_root_only():
    declared = _load_agents({"root": {"agent_id": "root-agent", "capabilities": []}})
    assert set(declared) == {"root-agent"}
    assert declared["root-agent"]["agent_id"] == "root-agent"


def test_load_agents_with_subagents_list_and_map():
    from_list = _load_agents(
        {
            "root": {"agent_id": "root-agent"},
            "agents": [{"agent_id": "child", "capabilities": [{"namespace": "files", "action": "read"}]}],
        }
    )
    assert set(from_list) == {"root-agent", "child"}
    assert from_list["child"]["capabilities"][0]["namespace"] == "files"

    from_map = _load_agents({"agents": {"child": {"delegation": {"max_depth": 2}}}})
    assert from_map["child"]["agent_id"] == "child"
    assert from_map["child"]["delegation"]["max_depth"] == 2


def test_load_agents_tolerates_empty_and_malformed():
    assert _load_agents({}) == {}
    assert _load_agents({"root": "not-a-dict", "agents": ["nope", 3]}) == {}
