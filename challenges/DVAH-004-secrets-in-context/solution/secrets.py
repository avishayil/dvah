"""FIXED secret broker: recursive redaction of the model context (INV-04)."""

from __future__ import annotations

from dvah.security.secrets import BuiltinSecretBroker

_SECRET = "AKIA-SECRET-123"


class FixedSecretBroker(BuiltinSecretBroker):
    def __init__(self) -> None:
        super().__init__(credentials={"aws": _SECRET})
