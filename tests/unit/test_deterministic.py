import textwrap

import pytest

from dvah.providers.deterministic import DeterministicModel
from dvah.providers.model import ModelRequest

pytestmark = pytest.mark.unit


def test_complete_returns_scripted_plan():
    model = DeterministicModel(scripts={"t": [{"namespace": "files", "action": "read", "resource": "/x"}]})
    resp = model.complete(ModelRequest(task_id="t"))
    assert resp.plan[0].namespace == "files"
    assert resp.plan[0].resource == "/x"


def test_complete_raises_for_unknown_task():
    model = DeterministicModel(scripts={})
    with pytest.raises(KeyError):
        model.complete(ModelRequest(task_id="missing"))


def test_from_yaml(tmp_path):
    path = tmp_path / "plans.yaml"
    path.write_text(textwrap.dedent(
        """
        t:
          - {namespace: files, action: read, resource: /x}
        """
    ))
    model = DeterministicModel.from_yaml(path)
    assert model.complete(ModelRequest(task_id="t")).plan[0].action == "read"


def test_from_yaml_empty_file(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    model = DeterministicModel.from_yaml(path)
    with pytest.raises(KeyError):
        model.complete(ModelRequest(task_id="t"))
