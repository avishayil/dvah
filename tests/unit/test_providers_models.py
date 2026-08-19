import pytest

from dvah.models.provenance import TrustLevel
from dvah.providers.model import ModelRequest, ModelResponse, PlanStep
from dvah.providers.tools import ToolResult

pytestmark = pytest.mark.unit


def test_plan_step_defaults():
    step = PlanStep(namespace="files", action="read", resource="/x")
    assert step.parameters == {}


def test_model_request_defaults():
    req = ModelRequest(task_id="t")
    assert req.prompt == ""
    assert req.context == ()


def test_model_response_holds_plan():
    resp = ModelResponse(plan=(PlanStep(namespace="a", action="b", resource="c"),))
    assert len(resp.plan) == 1


def test_tool_result_defaults():
    result = ToolResult(ok=True)
    assert result.output == {}
    assert result.trust is TrustLevel.UNTRUSTED_DATA
    assert result.source == ""
