"""Observation — a piece of tool output the agent has seen, with its provenance.

Accumulated on the RunContext so the context compiler can turn observations into the
model's context while preserving trust (the crux of INV-05/INV-06).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .provenance import TrustLevel


class Observation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    trust: TrustLevel
    content: dict = {}
