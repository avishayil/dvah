"""OpenAIAdapter — drive the harness with an OpenAI model (opt-in).

Import-safe: the ``openai`` package is imported lazily only when a real client is
needed. The model only proposes a plan; all authority flows through the
ActionEnvelope gate, so the harness stays model-agnostic.

Excluded from the invariant/property suite and from CI (needs a network + API key).
Enable via ``pip install -e '.[openai]'`` and ``OPENAI_API_KEY``.
"""

from __future__ import annotations

import os

import json

from ._planparse import SYSTEM_PROMPT, parse_steps, render_prompt
from .model import ModelRequest, ModelResponse, ToolCall

DEFAULT_MODEL = "gpt-4o"


class OpenAIAdapter:
    """A ModelProvider backed by the OpenAI Chat Completions API."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        client=None,
        max_tokens: int = 1024,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._client = client  # injectable for tests; built lazily otherwise
        self._max_tokens = max_tokens

    def _get_client(self):
        if self._client is None:
            import openai  # lazy: optional dependency

            self._client = openai.OpenAI(
                api_key=self._api_key or os.environ.get("OPENAI_API_KEY")
            )
        return self._client

    def complete(self, request: ModelRequest) -> ModelResponse:
        response = self._get_client().chat.completions.create(
            model=self._model,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": render_prompt(request)},
            ],
        )
        return ModelResponse(plan=parse_steps(_extract_text(response)))


def map_tool_calls(response) -> tuple[ToolCall, ...]:
    """Map an OpenAI Chat Completions ``message.tool_calls`` → ToolCalls.

    Each entry's ``function.name`` is treated as ``namespace.action`` and
    ``function.arguments`` (a JSON string) as the resource/parameters proposal.
    """
    message = _message(response)
    raw = _get(message, "tool_calls") or []
    calls: list[ToolCall] = []
    for tc in raw:
        fn = _get(tc, "function") or tc
        name = _get(fn, "name") or ""
        args_raw = _get(fn, "arguments") or "{}"
        args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
        namespace, _, action = name.partition(".")
        calls.append(
            ToolCall(
                namespace=namespace or name,
                action=action,
                resource=(args.get("resource", "") if isinstance(args, dict) else ""),
                parameters=(
                    {k: v for k, v in args.items() if k != "resource"}
                    if isinstance(args, dict)
                    else {}
                ),
            )
        )
    return tuple(calls)


def _message(response):
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices", [])
    if not choices:
        raise ValueError("openai response contained no choices")
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None and isinstance(first, dict):
        message = first.get("message", {})
    return message


def _get(obj, key):
    val = getattr(obj, key, None)
    if val is None and isinstance(obj, dict):
        val = obj.get(key)
    return val


def _extract_text(response) -> str:
    """Pull the assistant message text from a Chat Completions response (attr/dict)."""
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices", [])
    if not choices:
        raise ValueError("openai response contained no choices")
    first = choices[0]
    message = getattr(first, "message", None)
    if message is None and isinstance(first, dict):
        message = first.get("message", {})
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if not content:
        raise ValueError("openai response message had no content")
    return content
