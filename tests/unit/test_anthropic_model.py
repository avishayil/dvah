"""Unit tests for the Anthropic adapter — fully mocked, no network or API key."""

import pytest

from dvah.providers._planparse import parse_steps as _parse_plan
from dvah.providers.anthropic_model import AnthropicAdapter, _extract_text
from dvah.providers.model import ModelRequest


class _Block:
    def __init__(self, text):
        self.text = text


class _Message:
    def __init__(self, text):
        self.content = [_Block(text)]


class _FakeMessages:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _Message(self._text)


class _FakeClient:
    def __init__(self, text):
        self.messages = _FakeMessages(text)


@pytest.mark.unit
def test_complete_parses_plan_object():
    client = _FakeClient('{"plan": [{"namespace": "files", "action": "read", "resource": "/x"}]}')
    adapter = AnthropicAdapter(client=client)
    response = adapter.complete(ModelRequest(task_id="t", prompt="read x"))
    assert len(response.plan) == 1
    assert response.plan[0].namespace == "files"
    assert response.plan[0].action == "read"
    assert client.messages.calls[0]["model"] == "claude-sonnet-5"


@pytest.mark.unit
def test_complete_accepts_bare_list_and_code_fences():
    client = _FakeClient('```json\n[{"namespace": "github", "action": "issue.read", "resource": "r"}]\n```')
    adapter = AnthropicAdapter(client=client, model="claude-opus-5")
    response = adapter.complete(ModelRequest(task_id="t"))
    assert response.plan[0].namespace == "github"
    assert client.messages.calls[0]["model"] == "claude-opus-5"


@pytest.mark.unit
def test_extract_text_joins_blocks():
    assert _extract_text(_Message("hello")) == "hello"
    assert _extract_text({"content": [{"text": "a"}, {"text": "b"}]}) == "ab"


@pytest.mark.unit
def test_parse_plan_rejects_non_list():
    with pytest.raises(ValueError):
        _parse_plan('{"plan": {"not": "a list"}}')


@pytest.mark.unit
def test_adapter_is_model_provider_shaped():
    # Duck-typed against the ModelProvider protocol: has a callable complete().
    assert callable(AnthropicAdapter(client=_FakeClient("[]")).complete)
