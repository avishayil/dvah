"""Unit tests for BedrockAdapter — fully mocked, no network, no boto3 dependency."""

from __future__ import annotations

import json

import pytest

from dvah.providers.bedrock_model import DEFAULT_MODEL, BedrockAdapter
from dvah.providers.model import ModelRequest

pytestmark = pytest.mark.unit


class _FakeBedrockClient:
    def __init__(self, text: str) -> None:
        self._text = text
        self.captured: dict = {}

    def converse(self, **kwargs):
        self.captured = kwargs
        return {"output": {"message": {"content": [{"text": self._text}]}}}


def _plan_json() -> str:
    return json.dumps(
        {"plan": [{"namespace": "files", "action": "delete", "resource": "/tmp/x", "parameters": {}}]}
    )


def test_parses_converse_response():
    client = _FakeBedrockClient(_plan_json())
    resp = BedrockAdapter(client=client).complete(ModelRequest(task_id="t"))
    assert resp.plan[0].action == "delete"


def test_code_fenced_json_is_parsed():
    client = _FakeBedrockClient("```json\n" + _plan_json() + "\n```")
    resp = BedrockAdapter(client=client).complete(ModelRequest(task_id="t"))
    assert resp.plan[0].namespace == "files"


def test_empty_content_raises():
    client = _FakeBedrockClient("")
    with pytest.raises(ValueError):
        BedrockAdapter(client=client).complete(ModelRequest(task_id="t"))


def test_request_shape_passed_to_converse():
    client = _FakeBedrockClient(_plan_json())
    adapter = BedrockAdapter(client=client, model="us.meta.llama-x", max_tokens=512)
    adapter.complete(ModelRequest(task_id="tid", prompt="p", context=({"channel": "instruction"},)))
    kwargs = client.captured
    assert kwargs["modelId"] == "us.meta.llama-x"
    assert kwargs["inferenceConfig"]["maxTokens"] == 512
    assert kwargs["system"][0]["text"]  # system prompt present
    user_text = kwargs["messages"][0]["content"][0]["text"]
    assert "tid" in user_text and "p" in user_text


def test_default_model_id_is_a_bedrock_profile():
    assert DEFAULT_MODEL.endswith(":0") and "anthropic" in DEFAULT_MODEL


def test_module_imports_without_boto3():
    import importlib

    assert importlib.import_module("dvah.providers.bedrock_model") is not None
