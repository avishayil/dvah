"""The resolved Operation — the WHAT/WHERE/WITH-WHAT of an action.

An operation is only meaningful once *resolved*: namespace + action + concrete
resource + bound parameters. ``parameters_hash`` lets approvals bind to exact
argument values (INV-03).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .hashing import sha256_of


class Operation(BaseModel):
    """A concrete, resolved side-effectful operation ready for authorization."""

    model_config = ConfigDict(frozen=True)

    namespace: str
    action: str
    resource: str
    parameters: dict = {}

    @property
    def parameters_hash(self) -> str:
        return sha256_of(self.parameters)

    def with_parameters(self, parameters: dict) -> "Operation":
        return self.model_copy(update={"parameters": parameters})
