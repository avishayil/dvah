"""Unit tests for OpenAIAdapter — fully mocked, no network, no openai dependency."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from dvah.providers.model import ModelRequest
from dvah.providers.openai_model import DEFAULT_MODEL, OpenAIAdapter

pytestmark = pytest.mark.unit


class _FakeCompletions:
    def __init__(self, text: str) -> None:
        self._text = text
        self.captured: dict = {}

    def create(self, **kwargs):
        self.captured = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self._text))]
        )


class _FakeClient:
    def __init__(self, text: str) -> None:
        self._completions = _FakeCompletions(text)
        self.chat = SimpleNamespace(completions=self._completions)


def _plan_json() -> str:
    return json.dumps(
        {"plan": [{"namespace": "files", "action": "read", "resource": "/tmp/x", "parameters": {}}]}
    )


def test_parses_plan_object_into_steps():
    client = _FakeClient(_plan_json())
    adapter = OpenAIAdapter(client=client)
    resp = adapter.complete(ModelRequest(task_id="t"))
    assert len(resp.plan) == 1
    assert resp.plan[0].namespace == "files"
    assert resp.plan[0].action == "read"


def test_parses_bare_array():
    client = _FakeClient('[{"namespace": "github", "action": "issue.read", "resource": "r"}]')
    resp = OpenAIAdapter(client=client).complete(ModelRequest(task_id="t"))
    assert resp.plan[0].namespace == "github"


def test_malformed_output_raises():
    client = _FakeClient("not json at all")
    with pytest.raises(ValueError):
        OpenAIAdapter(client=client).complete(ModelRequest(task_id="t"))


def test_non_array_plan_raises():
    client = _FakeClient('{"plan": {"namespace": "x"}}')
    with pytest.raises(ValueError):
        OpenAIAdapter(client=client).complete(ModelRequest(task_id="t"))


def test_prompt_and_context_passed_through():
    client = _FakeClient(_plan_json())
    adapter = OpenAIAdapter(client=client, model="gpt-4o-mini", max_tokens=256)
    adapter.complete(
        ModelRequest(task_id="t42", prompt="do it", context=({"channel": "data"},))
    )
    kwargs = client.chat.completions.captured
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["max_tokens"] == 256
    user_msg = kwargs["messages"][-1]["content"]
    assert "t42" in user_msg and "do it" in user_msg


def test_default_model_id():
    assert DEFAULT_MODEL == "gpt-4o"


def test_module_imports_without_openai_package():
    import importlib

    assert importlib.import_module("dvah.providers.openai_model") is not None
