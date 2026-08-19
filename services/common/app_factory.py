"""Factory for a minimal FastAPI service with health + reset + recorder endpoints.

``create_service`` returns an app that already exposes ``GET /_health``,
``POST /_reset``, and ``GET /_recorder``. The caller passes a ``reset_fn`` that
re-seeds its backing store from the JSON body, then registers its own domain routes.

Every service carries a DVAH-controlled **recorder** (``app.state.recorder``): the
authoritative log of the side effects a service actually performed. Domain routes call
``app.state.recorder.record(...)`` on each mutating operation. Grader-observed
conformance reads ``GET /_recorder`` to check what really happened against what an
adapter *claims* it did — so a dishonest adapter can't attest a pass it didn't earn.
``POST /_reset`` clears the recorder alongside re-seeding the store.
"""

from __future__ import annotations

from typing import Callable

from fastapi import FastAPI, Request


class Recorder:
    """Ordered, in-memory log of the mutating side effects a service performed."""

    def __init__(self) -> None:
        self._events: list[dict] = []

    def record(self, **event: object) -> None:
        self._events.append(dict(event))

    def events(self) -> list[dict]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()


def create_service(name: str, reset_fn: Callable[[dict], None]) -> FastAPI:
    app = FastAPI(title=f"dvah-{name}")
    recorder = Recorder()
    app.state.recorder = recorder

    @app.get("/_health")
    def health() -> dict:
        return {"ok": True, "service": name}

    @app.post("/_reset")
    async def reset(request: Request) -> dict:
        try:
            seed = await request.json()
        except Exception:
            seed = {}
        recorder.clear()
        reset_fn(seed or {})
        return {"ok": True}

    @app.get("/_recorder")
    def recorded() -> dict:
        return {"recorder": recorder.events()}

    return app
