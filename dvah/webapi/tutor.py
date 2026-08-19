"""Optional AI tutor — a Socratic coach over the model adapters.

Disabled unless ``DVAH_TUTOR=1``. The provider is chosen by ``DVAH_TUTOR_PROVIDER``
(anthropic|openai|bedrock) and needs that provider's credentials. The tutor is prompted
to guide, not to hand over the full solution unless explicitly asked.
"""

from __future__ import annotations

import os

_SYSTEM = (
    "You are a Socratic security tutor inside DVAH, a lab that teaches agent-runtime "
    "security invariants. The learner is patching intentionally vulnerable code. Guide "
    "them toward the broken trust boundary with questions and concepts. Do NOT reveal "
    "the full solution diff unless the learner explicitly asks for it. Be concise."
)


def is_enabled() -> bool:
    from .settings import SETTINGS

    return SETTINGS.tutor_enabled() and SETTINGS.tutor_ready()


def _provider():
    from .settings import SETTINGS

    provider = SETTINGS.tutor_provider()
    model = SETTINGS.tutor_model()
    key = SETTINGS.api_key(provider)
    if provider == "openai":
        from ..providers.openai_model import OpenAIAdapter

        kw = {"api_key": key} if key else {}
        if model:
            kw["model"] = model
        return OpenAIAdapter(**kw)
    if provider == "bedrock":
        from ..providers.bedrock_model import BedrockAdapter

        kw = {"api_key": key} if key else {}
        if model:
            kw["model"] = model
        return BedrockAdapter(**kw)
    from ..providers.anthropic_model import AnthropicAdapter

    kw = {"api_key": key} if key else {}
    if model:
        kw["model"] = model
    return AnthropicAdapter(**kw)


def _build_prompt(code: dict[str, str], failing: list[str], trace_summary: dict, question: str | None) -> str:
    lines = ["The learner's current vulnerable code:"]
    for path, contents in code.items():
        lines.append(f"\n### {path}\n{contents}")
    if failing:
        lines.append("\nFailing tests: " + ", ".join(failing))
    if trace_summary:
        lines.append(f"\nTrace summary: {trace_summary}")
    lines.append("\nLearner question: " + (question or "I'm stuck — nudge me toward the issue."))
    return "\n".join(lines)


def coach(code: dict[str, str], failing: list[str], trace_summary: dict, question: str | None) -> str:
    """Call the configured model adapter with a Socratic prompt; return the reply text.

    Uses the adapter's ``complete`` (plan-shaped) contract minimally: we send the coaching
    prompt and read back text. Adapters here return a plan, so the tutor instead builds a
    direct chat call when the SDK is present; kept import-safe and behind the feature flag.
    """
    from ..providers._planparse import render_prompt  # noqa: F401 - shared serialization
    from ..providers.model import ModelRequest

    provider = _provider()
    prompt = _build_prompt(code, failing, trace_summary, question)
    # The adapters are plan-oriented; reuse the same client but ask for prose. We call
    # the adapter's underlying client via a thin text request when available.
    request = ModelRequest(task_id="tutor", prompt=f"{_SYSTEM}\n\n{prompt}")
    reply = _text_complete(provider, request)
    return reply


def _text_complete(provider, request) -> str:  # pragma: no cover - needs live SDK/key
    """Best-effort prose completion across adapters (kept out of CI)."""
    client = provider._get_client()
    model = getattr(provider, "_model", None)
    # Anthropic
    if hasattr(client, "messages"):
        msg = client.messages.create(
            model=model, max_tokens=512,
            system=_SYSTEM,
            messages=[{"role": "user", "content": request.prompt}],
        )
        return "".join(getattr(b, "text", "") for b in getattr(msg, "content", []))
    # OpenAI
    if hasattr(client, "chat"):
        resp = client.chat.completions.create(
            model=model, max_tokens=512,
            messages=[{"role": "system", "content": _SYSTEM},
                      {"role": "user", "content": request.prompt}],
        )
        return resp.choices[0].message.content
    # Bedrock — apply the Bedrock API key (bearer token) for the scope of the call,
    # exactly as BedrockAdapter.complete does. Calling converse() directly (as this
    # thin prose path does) would otherwise skip that scoping and fail auth even with a
    # valid UI/env key — the cause of the tutor-test 502.
    from ..providers.bedrock_model import _bearer_env

    with _bearer_env(getattr(provider, "_api_key", None)):
        resp = client.converse(
            modelId=model, system=[{"text": _SYSTEM}],
            messages=[{"role": "user", "content": [{"text": request.prompt}]}],
            inferenceConfig={"maxTokens": 512},
        )
    return "".join(b.get("text", "") for b in resp["output"]["message"]["content"])
