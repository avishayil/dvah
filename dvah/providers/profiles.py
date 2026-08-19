"""Model profiles — decouple a scenario from a hardcoded provider.

A lab (or the UI) can declare a *profile* (``balanced``/``smart``/``cheap``/``local``)
instead of naming a provider, so security semantics never depend on a specific model.
Each profile maps to a ``(provider, model_id)`` pair; the mapping is config-driven via
``DVAH_PROFILE_<NAME>`` env overrides (e.g. ``DVAH_PROFILE_BALANCED=openai:gpt-4o``).

``deterministic`` is always available and is the default when no live profile/keys are
configured — it is the CI oracle.
"""

from __future__ import annotations

import os

#: Profile → (provider, model_id). ``None`` model_id means "adapter default".
DEFAULT_PROFILES: dict[str, tuple[str, str | None]] = {
    "deterministic": ("deterministic", None),
    "balanced": ("openai", "gpt-4o"),
    "smart": ("anthropic", "claude-sonnet-5"),
    "cheap": ("openai", "gpt-4o-mini"),
    "local": ("ollama", "llama3.1"),
}

#: Raw provider names accepted directly as a selection (adapter default model). Keeps
#: ``--model bedrock`` / the in-app live provider working instead of silently degrading.
_RAW_PROVIDERS = ("anthropic", "openai", "bedrock", "ollama")


def resolve_profile(name: str, env: dict[str, str] | None = None) -> tuple[str, str | None]:
    """Resolve a profile name to ``(provider, model_id)``.

    An env override ``DVAH_PROFILE_<NAME>`` of the form ``provider`` or ``provider:model``
    takes precedence. Unknown names fall back to ``deterministic`` (never raises, so a
    misconfigured profile degrades to the safe oracle rather than crashing a run).
    """
    env = env if env is not None else dict(os.environ)
    key = name.strip().lower()
    override = env.get(f"DVAH_PROFILE_{key.upper()}")
    if override:
        provider, _, model = override.partition(":")
        return provider.strip(), (model.strip() or None)
    if key in DEFAULT_PROFILES:
        return DEFAULT_PROFILES[key]
    if key in _RAW_PROVIDERS:  # a bare provider name selects that provider directly
        return key, None
    return DEFAULT_PROFILES["deterministic"]
