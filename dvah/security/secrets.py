"""Secret broker (INV-04): credentials are execution plumbing, never in the model.

The correct default *resolves* a namespace's credential and hands it to the tool layer
as a separate execution-time argument — it is never written into the resolved
operation's parameters. That keeps the executed operation byte-for-byte identical to the
authorized one (so ``action_hash`` still describes exactly what ran) and keeps the
credential out of both ``Operation.parameters`` and the model context.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.operation import Operation


@runtime_checkable
class SecretBroker(Protocol):
    def resolve(self, namespace: str, operation: Operation) -> str | None: ...
    def redact_for_model(self, context: tuple[dict, ...]) -> tuple[dict, ...]: ...


class BuiltinSecretBroker:
    """Correct reference broker: hands credentials to the tool layer, redacts context."""

    def __init__(self, credentials: dict[str, str] | None = None) -> None:
        self._credentials = credentials or {}

    def resolve(self, namespace: str, operation: Operation) -> str | None:
        """Return the credential handle for a namespace (a real broker would fetch a
        short-lived token from a vault). Never mutates ``operation``."""
        return self._credentials.get(namespace)

    def redact_for_model(self, context: tuple[dict, ...]) -> tuple[dict, ...]:
        """Defense-in-depth (credentials shouldn't reach context assembly in the first
        place — see the module docstring). Drop any top-level key whose value *is* a
        secret, and mask secrets appearing anywhere deeper, including as substrings of a
        larger string."""
        secret_values = set(self._credentials.values())
        return tuple(
            {
                k: _mask(v, secret_values)
                for k, v in item.items()
                if not (isinstance(v, str) and v in secret_values)
            }
            for item in context
        )


_REDACTED = "***REDACTED***"


def _redact_str(text: str, secret_values) -> str:
    """Mask every secret that appears *anywhere* in ``text`` — not only when the whole
    string equals a credential. Defense-in-depth: a secret embedded in a larger string
    (``"Authorization: Bearer <secret>"``) must not survive into the model context."""
    for secret in secret_values:
        if secret and secret in text:  # skip empty secrets to avoid pathological replace
            text = text.replace(secret, _REDACTED)
    return text


def _mask(value, secret_values):
    if isinstance(value, str):
        return _redact_str(value, secret_values)
    if isinstance(value, dict):
        return {k: _mask(v, secret_values) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_mask(v, secret_values) for v in value)
    return value
