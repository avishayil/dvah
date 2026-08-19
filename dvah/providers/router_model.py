"""Model router — selection + fallback across model sessions.

Picks a ``ModelSession`` from a profile/provider selection and, on a provider error,
falls through a configured chain (emitting a ``model.fallback`` trace event so a silent
switch to a differently-behaving model is observable). The deterministic session is the
default and the last-resort fallback — the CI oracle. Live adapters are built lazily and
only when selected, so this stays import-safe without any SDK installed.
"""

from __future__ import annotations

from typing import Callable

from .model import AgentState, Message, ModelProvider, ModelRequest, ModelTurn
from .profiles import resolve_profile
from .session import ScriptedSession


class LiveSession:
    """Adapt a live ``ModelProvider`` adapter to the ``ModelSession`` interface.

    Turn-by-turn reactive live execution (feeding observations back) arrives with the
    live/replay work; here a live turn proposes the adapter's plan as one turn's tool
    calls, tagged with the provider identity. The per-call security gate is identical.
    """

    def __init__(
        self, provider: ModelProvider, task_id: str, prompt: str = "",
        context: tuple[dict, ...] = (), identity: str = "live",
    ) -> None:
        self._provider = provider
        self._task_id = task_id
        self._prompt = prompt
        self._context = context
        self._identity = identity
        self._emitted = False

    def next(
        self, messages: tuple[Message, ...], tools: tuple[str, ...], state: AgentState,
    ) -> ModelTurn:
        if self._emitted:
            return ModelTurn(final=True)
        self._emitted = True
        resp = self._provider.complete(
            ModelRequest(task_id=self._task_id, prompt=self._prompt, context=self._context)
        )
        from .model import ToolCall

        calls = tuple(
            ToolCall(namespace=s.namespace, action=s.action, resource=s.resource,
                     parameters=s.parameters)
            for s in resp.plan
        )
        return ModelTurn(tool_calls=calls, final=True, model_identity=self._identity)


class ModelRouter:
    """A ``ModelSession`` that delegates to the first candidate that doesn't error.

    ``candidates`` is an ordered tuple of ``(label, factory)``; sessions are built lazily
    so a provider that fails to construct also triggers fallback. On any error from the
    active session's ``next``, emits ``model.fallback`` and advances to the next candidate.
    """

    def __init__(
        self,
        candidates: tuple[tuple[str, Callable[[], object]], ...],
        trace=None,
        task_id: str = "",
    ) -> None:
        if not candidates:
            raise ValueError("ModelRouter needs at least one candidate")
        self._candidates = candidates
        self._trace = trace
        self._task_id = task_id
        self._idx = 0
        self._active = None

    @property
    def fallback_chain(self) -> tuple[str, ...]:
        return tuple(label for label, _ in self._candidates)

    def _session(self):
        if self._active is None:
            _, factory = self._candidates[self._idx]
            self._active = factory()
        return self._active

    def next(
        self, messages: tuple[Message, ...], tools: tuple[str, ...], state: AgentState,
    ) -> ModelTurn:
        while True:
            try:
                return self._session().next(messages, tools, state)
            except Exception as exc:  # provider/build error → fall through
                cur_label = self._candidates[self._idx][0]
                if self._idx + 1 >= len(self._candidates):
                    raise
                nxt_label = self._candidates[self._idx + 1][0]
                if self._trace is not None:
                    self._trace.emit(
                        "model.fallback", self._task_id,
                        **{"from": cur_label, "to": nxt_label, "error": str(exc)},
                    )
                self._idx += 1
                self._active = None


def _build_live(provider: str, model_id: str | None, api_key: str | None = None):
    """Lazily build a live adapter for a provider name (import-safe).

    ``api_key`` (when supplied) is passed to the adapter — this is how a UI/Settings key
    reaches the *live* model path (for Bedrock it becomes the bearer token). Adapters keep
    their env fallback when it's None.
    """
    key_kw = {"api_key": api_key} if api_key else {}
    if provider == "anthropic":
        from .anthropic_model import AnthropicAdapter, DEFAULT_MODEL
        return AnthropicAdapter(model=model_id or DEFAULT_MODEL, **key_kw)
    if provider == "openai":
        from .openai_model import OpenAIAdapter, DEFAULT_MODEL
        return OpenAIAdapter(model=model_id or DEFAULT_MODEL, **key_kw)
    if provider == "bedrock":
        from .bedrock_model import BedrockAdapter, DEFAULT_MODEL
        return BedrockAdapter(model=model_id or DEFAULT_MODEL, **key_kw)
    raise ValueError(f"no live adapter for provider {provider!r}")


def build_model_session(
    selection: str,
    *,
    deterministic_provider: ModelProvider,
    task_id: str,
    prompt: str = "",
    context: tuple[dict, ...] = (),
    trace=None,
    env: dict[str, str] | None = None,
    get_key: Callable[[str], str | None] | None = None,
) -> ModelRouter:
    """Build a routed ``ModelSession`` for a profile or provider ``selection``.

    ``deterministic`` → the scripted CI oracle. Any other selection resolves through
    profiles to a live provider, with the deterministic oracle appended as the final
    fallback so a missing key/SDK degrades safely rather than crashing a run.

    ``get_key(provider)`` supplies the credential for the resolved provider (e.g. the
    in-app live-run passes ``SETTINGS.api_key``); the CLI omits it and relies on env.
    """
    provider, model_id = resolve_profile(selection, env)
    det = (
        "deterministic",
        lambda: ScriptedSession(deterministic_provider, task_id, context),
    )
    if provider == "deterministic":
        return ModelRouter((det,), trace=trace, task_id=task_id)
    key = get_key(provider) if get_key else None
    primary = (
        provider,
        lambda: LiveSession(
            _build_live(provider, model_id, api_key=key), task_id, prompt, context,
            identity=provider,
        ),
    )
    return ModelRouter((primary, det), trace=trace, task_id=task_id)
