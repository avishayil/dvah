"""AnthropicAdapter — drive the harness with a real Claude model (opt-in).

Import-safe: the ``anthropic`` package is imported lazily only when a real client is
needed, so this module loads even when the optional dependency is absent. The model
only proposes a plan; all authority still flows through the ActionEnvelope gate, so
the harness and every security test remain model-agnostic.

Excluded from the invariant/property suite and from CI (needs a network + API key).
Enable via ``pip install -e '.[anthropic]'`` and ``ANTHROPIC_API_KEY``.
"""

from __future__ import annotations

import os

from ._planparse import SYSTEM_PROMPT, parse_steps, render_prompt
from .model import ModelRequest, ModelResponse, PlanStep, ToolCall

DEFAULT_MODEL = "claude-sonnet-5"


class AnthropicAdapter:
    """A ModelProvider backed by the Anthropic Messages API."""

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
            import anthropic  # lazy: optional dependency

            self._client = anthropic.Anthropic(
                api_key=self._api_key or os.environ.get("ANTHROPIC_API_KEY")
            )
        return self._client

    def complete(self, request: ModelRequest) -> ModelResponse:
        message = self._get_client().messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": render_prompt(request)}],
        )
        return ModelResponse(plan=parse_steps(_extract_text(message)))


def _extract_text(message) -> str:
    """Join the text blocks of an Anthropic Message (attr or dict form)."""
    parts: list[str] = []
    for block in _blocks(message):
        text = _get(block, "text")
        if text:
            parts.append(text)
    return "".join(parts)


def map_tool_calls(message) -> tuple[ToolCall, ...]:
    """Map an Anthropic Message's ``tool_use`` content blocks → ToolCalls.

    Each ``tool_use`` block names a tool and carries ``input`` args. We treat the tool
    name as ``namespace.action`` (dot-split) and the input as the proposal's
    resource/parameters — a proposal only; the harness still confers authority.
    """
    calls: list[ToolCall] = []
    for block in _blocks(message):
        if _get(block, "type") != "tool_use":
            continue
        name = _get(block, "name") or ""
        args = _get(block, "input") or {}
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


def _blocks(message):
    blocks = getattr(message, "content", None)
    if blocks is None and isinstance(message, dict):
        blocks = message.get("content", [])
    return blocks or []


def _get(block, key):
    val = getattr(block, key, None)
    if val is None and isinstance(block, dict):
        val = block.get(key)
    return val
