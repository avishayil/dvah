"""Grader-observed conformance.

The default battery trusts an adapter's *self-reported* observables (e.g.
``RunOutcome.executed_hashes``). That's self-attestation — a dishonest or buggy
adapter can report a pass it never earned. This module grounds the **observable**
invariants in DVAH-controlled state: it reads what the mock services actually
RECORDED (``GET /_recorder``) and reconciles that against what the adapter CLAIMS
it executed. A claim with no matching recorded side effect (or a recorded side
effect the adapter didn't own) fails.

The reconcile logic here is pure and offline-testable; wiring it to live services
lives in the e2e-marked tests. Side effects are normalized to
``(namespace, action, resource)`` triples.
"""

from __future__ import annotations

from typing import Iterable

from .adapter import ConformanceResult

SideEffect = tuple[str, str, str]  # (namespace, action, resource)


def observed_side_effects(events: Iterable[dict]) -> list[SideEffect]:
    """Normalize a service ``/_recorder`` event list to successful side effects."""
    out: list[SideEffect] = []
    for e in events:
        if not e.get("ok", True):
            continue  # a denied/failed attempt is not a side effect
        out.append((str(e.get("namespace", "")), str(e.get("action", "")),
                    str(e.get("resource", ""))))
    return sorted(out)


def reconcile(claimed: Iterable[SideEffect], observed: Iterable[SideEffect],
              invariant: str = "INV-01-observed") -> ConformanceResult:
    """Pass iff the adapter's claimed side effects exactly match what DVAH observed."""
    c = sorted(tuple(x) for x in claimed)
    o = sorted(tuple(x) for x in observed)
    ok = c == o
    detail = ("observed side effects match the adapter's self-report" if ok
              else f"self-report ≠ observed — claimed {c}, DVAH recorded {o}")
    return ConformanceResult(invariant, ok, detail)


def read_recorder(base_url: str) -> list[dict]:
    """Read a service's authoritative side-effect log (lazy httpx import)."""
    import httpx

    return httpx.get(f"{base_url}/_recorder", timeout=5.0).json()["recorder"]


def reset_service(base_url: str, seed: dict | None = None) -> None:
    import httpx

    httpx.post(f"{base_url}/_reset", json=seed or {}, timeout=5.0)
