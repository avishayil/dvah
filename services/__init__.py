"""Real FastAPI apps for the simulated external systems (M2).

Each service wraps a seedable in-memory store and exposes ``POST /_reset`` and
``GET /_health`` for deterministic e2e testing. Behavior mirrors the in-process
stores in ``dvah.services.memory`` so the harness behaves identically across
transports.
"""
