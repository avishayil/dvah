"""Authorization decision types shared across the security layer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    NEEDS_APPROVAL = "needs_approval"


class Decision(BaseModel):
    """The outcome of a policy evaluation, with the driving invariant on a DENY."""

    model_config = ConfigDict(frozen=True)

    verdict: Verdict
    reason: str
    invariant: str | None = None


class Denied(Exception):
    """Raised when the broker refuses to execute an action."""

    def __init__(self, decision: Decision) -> None:
        self.decision = decision
        super().__init__(f"{decision.invariant or 'DENY'}: {decision.reason}")
