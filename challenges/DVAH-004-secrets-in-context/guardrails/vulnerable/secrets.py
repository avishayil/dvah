"""VULNERABLE secret broker: no redaction of the model context (INV-04)."""

from __future__ import annotations

from dvah.guardrails.secrets import BuiltinSecretBroker

_SECRET = "AKIA-SECRET-123"


class ContextInliningSecretBroker(BuiltinSecretBroker):
    def __init__(self) -> None:
        super().__init__(credentials={"aws": _SECRET})

    def redact_for_model(self, context):
        return context  # BUG: the credential reaches the model untouched
