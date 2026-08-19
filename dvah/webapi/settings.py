"""Runtime configuration settings, editable from the UI.

Overrides are process-local and **in memory only** — API keys entered in the UI are
never written to disk and never returned in plaintext (only a masked hint + a boolean).
Values fall back to environment variables when no UI override is set. For production,
prefer env / a secrets manager over the UI.
"""

from __future__ import annotations

import os

PROVIDERS = ("anthropic", "openai", "bedrock")

# Which env var holds each provider's credential. Bedrock supports a Bedrock API key
# (bearer token in AWS_BEARER_TOKEN_BEDROCK); it can also use the wider AWS chain.
_ENV_KEY = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "bedrock": "AWS_BEARER_TOKEN_BEDROCK",
}


def _bedrock_env_ready() -> bool:
    """True if the server can reach Bedrock via a key, access key, or profile/role."""
    return any(
        os.environ.get(v)
        for v in ("AWS_BEARER_TOKEN_BEDROCK", "AWS_ACCESS_KEY_ID", "AWS_PROFILE")
    )


RUN_MODES = ("deterministic", "live")


class RuntimeSettings:
    def __init__(self) -> None:
        self._tutor_enabled: bool | None = None
        self._provider: str | None = None
        self._model: str | None = None
        self._api_keys: dict[str, str] = {}  # provider -> key (memory only)
        self._run_mode: str | None = None  # deterministic (default) | live

    # --- resolution (UI override wins over env) -----------------------------
    def tutor_enabled(self) -> bool:
        if self._tutor_enabled is not None:
            return self._tutor_enabled
        return os.environ.get("DVAH_TUTOR") == "1"

    def tutor_provider(self) -> str:
        return self._provider or os.environ.get("DVAH_TUTOR_PROVIDER", "anthropic")

    def tutor_model(self) -> str | None:
        return self._model

    def api_key(self, provider: str) -> str | None:
        return self._api_keys.get(provider) or os.environ.get(_ENV_KEY.get(provider, ""))

    def key_source(self, provider: str) -> str | None:
        if provider in self._api_keys:
            return "ui"
        if os.environ.get(_ENV_KEY.get(provider, "")):
            return "env"
        return None

    def model_ready(self) -> bool:
        """True if credentials for the configured provider are available (UI or env).

        Shared by the AI tutor and the live agent-run path — not tutor-specific.
        """
        provider = self.tutor_provider()
        if provider == "bedrock":
            # Ready with a Bedrock API key (UI or env) or any AWS credential source.
            return self.api_key("bedrock") is not None or _bedrock_env_ready()
        return self.api_key(provider) is not None

    # Back-compat alias (older callers referenced tutor_ready).
    def tutor_ready(self) -> bool:
        return self.model_ready()

    def run_mode(self) -> str:
        """The single global run mode: 'deterministic' (default/CI oracle) or 'live'.

        Live is only *effective* when a model key is configured; callers still gate on
        credentials. Replay is a CLI-only path and intentionally not a UI mode.
        """
        return self._run_mode or "deterministic"

    # --- mutation -----------------------------------------------------------
    def update(
        self,
        *,
        tutor_enabled: bool | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        run_mode: str | None = None,
    ) -> None:
        if provider is not None:
            if provider not in PROVIDERS:
                raise ValueError(f"unknown provider {provider!r}")
            self._provider = provider
        if run_mode is not None:
            if run_mode not in RUN_MODES:
                raise ValueError(f"unknown run_mode {run_mode!r}")
            self._run_mode = run_mode
        if tutor_enabled is not None:
            self._tutor_enabled = tutor_enabled
        if model is not None:
            self._model = model.strip() or None
        if api_key:  # store under the (now-current) provider; never logged/echoed
            self._api_keys[self.tutor_provider()] = api_key


SETTINGS = RuntimeSettings()


def _mask(key: str | None) -> str | None:
    if not key:
        return None
    return "…" + key[-4:] if len(key) >= 4 else "…"


def view() -> dict:
    """Non-secret snapshot for the UI."""
    provider = SETTINGS.tutor_provider()
    key = SETTINGS.api_key(provider)
    return {
        "providers": list(PROVIDERS),
        "run_modes": list(RUN_MODES),
        "run_mode": SETTINGS.run_mode(),
        # Generic model credentials — shared by the AI tutor AND live agent runs.
        "model": {
            "ready": SETTINGS.model_ready(),
            "provider": provider,
            "model": SETTINGS.tutor_model(),
            "key_set": key is not None,
            "key_hint": _mask(key),
            "key_source": SETTINGS.key_source(provider),
        },
        # The optional AI tutor is just an on/off feature that shares the model above.
        "tutor": {
            "enabled": SETTINGS.tutor_enabled(),
        },
        "env_keys": {
            "anthropic": bool(os.environ.get(_ENV_KEY["anthropic"])),
            "openai": bool(os.environ.get(_ENV_KEY["openai"])),
            "bedrock": _bedrock_env_ready(),
        },
        "server": {
            "runner": os.environ.get("DVAH_RUNNER", "subprocess"),
            "run_concurrency": os.environ.get("DVAH_RUN_CONCURRENCY", "2"),
            "cors_origins": os.environ.get("DVAH_CORS_ORIGINS", "*"),
        },
    }
