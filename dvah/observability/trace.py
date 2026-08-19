"""Security trace — the audit spine of the harness.

Every lifecycle step emits a TraceEvent. Invariant tests query the log to assert
properties like "every executed action was authorized at execution time" (INV-01).
``dvah trace`` renders the log for a task.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, ConfigDict


class TraceEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str  # "envelope.built" | "policy.decision" | "executed" | "denied" | ...
    task_id: str
    action_hash: str | None = None
    # Occurrence identity: the *semantic* action_hash answers "what action", while
    # action_id answers "which execution occurrence". Complete mediation (INV-01) is an
    # occurrence property — authorizing an action once must not license executing it twice.
    action_id: str | None = None
    detail: dict = {}


class TraceLog:
    """Append-only, queryable event log for a run."""

    def __init__(self) -> None:
        self._events: list[TraceEvent] = []

    def emit(
        self,
        kind: str,
        task_id: str,
        action_hash: str | None = None,
        action_id: str | None = None,
        **detail: Any,
    ) -> None:
        self._events.append(
            TraceEvent(
                kind=kind,
                task_id=task_id,
                action_hash=action_hash,
                action_id=action_id,
                detail=detail,
            )
        )

    @property
    def events(self) -> tuple[TraceEvent, ...]:
        return tuple(self._events)

    def of_kind(self, kind: str) -> list[TraceEvent]:
        return [e for e in self._events if e.kind == kind]

    def authorized_hashes(self) -> set[str]:
        """Action hashes that received an ALLOW/approved decision at execution time."""
        return {
            e.action_hash
            for e in self._events
            if e.kind == "policy.decision"
            and e.detail.get("verdict") in {"allow", "needs_approval"}
            and e.action_hash is not None
        }

    def executed_hashes(self) -> list[str]:
        return [e.action_hash for e in self._events if e.kind == "executed" and e.action_hash]

    def unauthorized_executions(self) -> list[str]:
        """Executed occurrences with no matching authorization (INV-01, complete mediation).

        Occurrence-level, not set-membership: each ``executed`` event must be paired 1:1
        with a *distinct*, *preceding* allowing ``policy.decision`` for the same
        ``(action_id, action_hash)``. A single authorization therefore licenses exactly
        one execution — replaying the same resolved action a second time without a fresh
        decision is flagged, even though its hash was authorized once (review finding #1).
        """
        credits: Counter[tuple[str | None, str]] = Counter()
        unauthorized: list[str] = []
        for e in self._events:
            if e.action_hash is None:
                continue
            key = (e.action_id, e.action_hash)
            if (
                e.kind == "policy.decision"
                and e.detail.get("verdict") in {"allow", "needs_approval"}
            ):
                credits[key] += 1
            elif e.kind == "executed":
                if credits[key] > 0:
                    credits[key] -= 1  # this execution consumes one authorization
                else:
                    unauthorized.append(e.action_hash)
        return unauthorized
