import pytest

from dvah.providers.model import ModelRequest
from dvah.providers.reactive import ContextActionModel


@pytest.mark.unit
def test_scripted_plan_is_replayed():
    model = ContextActionModel(scripts={"t": [{"namespace": "files", "action": "read", "resource": "/x"}]})
    resp = model.complete(ModelRequest(task_id="t"))
    assert resp.plan[0].resource == "/x"


@pytest.mark.unit
def test_reacts_to_action_embedded_in_instruction_item():
    model = ContextActionModel(scripts={})
    ctx = (
        {"channel": "instruction", "trust": "untrusted_data", "source": "issue",
         "content": {"issues": [{"id": 1, "action": {"namespace": "github", "action": "issue.comment", "resource": "r"}}]}},
    )
    resp = model.complete(ModelRequest(task_id="unscripted", context=ctx))
    assert len(resp.plan) == 1
    assert (resp.plan[0].namespace, resp.plan[0].action) == ("github", "issue.comment")


@pytest.mark.unit
def test_ignores_actions_in_data_channel():
    model = ContextActionModel(scripts={})
    ctx = (
        {"channel": "data", "content": {"action": {"namespace": "github", "action": "issue.comment", "resource": "r"}}},
    )
    resp = model.complete(ModelRequest(task_id="unscripted", context=ctx))
    assert resp.plan == ()
