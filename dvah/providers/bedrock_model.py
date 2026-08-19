"""BedrockAdapter — drive the harness with a model hosted on AWS Bedrock (opt-in).

Import-safe: ``boto3`` is imported lazily only when a real client is needed. Uses the
Bedrock Runtime ``converse`` API, which gives a provider-agnostic message shape across
Bedrock-hosted models (Anthropic, Llama, Titan, …). The model only proposes a plan;
authority flows through the ActionEnvelope gate.

Excluded from the invariant/property suite and from CI (needs AWS credentials + a
network). Enable via ``pip install -e '.[bedrock]'`` and standard AWS env/profile.
"""

from __future__ import annotations

import contextlib
import os

from ._planparse import SYSTEM_PROMPT, parse_steps, render_prompt
from .model import ModelRequest, ModelResponse, ToolCall


@contextlib.contextmanager
def _bearer_env(token: str | None):
    """Temporarily set AWS_BEARER_TOKEN_BEDROCK, then restore — no global pollution."""
    if not token:
        yield
        return
    key = "AWS_BEARER_TOKEN_BEDROCK"
    prev = os.environ.get(key)
    os.environ[key] = token
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = prev

#: A Bedrock inference-profile / model id. Override per account/region as needed.
DEFAULT_MODEL = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


class BedrockAdapter:
    """A ModelProvider backed by the AWS Bedrock Runtime ``converse`` API."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        region: str | None = None,
        api_key: str | None = None,
        client=None,
        max_tokens: int = 1024,
    ) -> None:
        self._model = model
        self._region = region
        # A Bedrock API key (bearer token). If unset, the standard AWS credential
        # chain (env keys / profile / role) is used instead.
        self._api_key = api_key
        self._client = client  # injectable for tests; built lazily otherwise
        self._max_tokens = max_tokens

    def _get_client(self):
        if self._client is None:
            import boto3  # lazy: optional dependency

            # boto3 authenticates Bedrock via the AWS_BEARER_TOKEN_BEDROCK env var when a
            # Bedrock API key is supplied; otherwise it falls back to the AWS chain. The
            # var is set only for the scope of the API call (see complete()), never
            # persisted to the process environment.
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=self._region or os.environ.get("AWS_REGION"),
            )
        return self._client

    def complete(self, request: ModelRequest) -> ModelResponse:
        with _bearer_env(self._api_key):
            client = self._get_client()
            response = client.converse(
                modelId=self._model,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": render_prompt(request)}]}],
                inferenceConfig={"maxTokens": self._max_tokens},
            )
        return ModelResponse(plan=parse_steps(_extract_text(response)))


def _extract_text(response) -> str:
    """Join the text blocks of a Bedrock ``converse`` response."""
    message = response.get("output", {}).get("message", {})
    parts = [block.get("text", "") for block in message.get("content", [])]
    text = "".join(parts)
    if not text:
        raise ValueError("bedrock response contained no text content")
    return text


def map_tool_calls(response) -> tuple[ToolCall, ...]:
    """Map a Bedrock ``converse`` response's ``toolUse`` blocks → ToolCalls.

    Each ``toolUse`` block has ``name`` (treated as ``namespace.action``) and ``input``
    (the resource/parameters proposal).
    """
    message = response.get("output", {}).get("message", {})
    calls: list[ToolCall] = []
    for block in message.get("content", []):
        use = block.get("toolUse") if isinstance(block, dict) else None
        if not use:
            continue
        name = use.get("name", "")
        args = use.get("input", {}) or {}
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
