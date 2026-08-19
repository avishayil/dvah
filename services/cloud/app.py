"""Cloud service (port 8004) — in-memory instances.

    GET  /cloud/instances                   -> list instances
    POST /cloud/instances/{id}/terminate    -> terminate one
"""

from __future__ import annotations

from services.common.app_factory import create_service


class InstanceStore:
    def __init__(self) -> None:
        self._instances: dict[str, dict] = {}

    def reset(self, seed: dict) -> None:
        self._instances = dict(seed.get("cloud", {}))

    def list(self) -> list[dict]:
        return [{"id": k, **v} for k, v in self._instances.items()]

    def terminate(self, instance_id: str) -> bool:
        existed = instance_id in self._instances
        self._instances.pop(instance_id, None)
        return existed


store = InstanceStore()
app = create_service("cloud", store.reset)


@app.get("/cloud/instances")
def instances() -> dict:
    return {"instances": store.list()}


@app.post("/cloud/instances/{instance_id}/terminate")
def terminate(instance_id: str) -> dict:
    ok = store.terminate(instance_id)
    app.state.recorder.record(namespace="cloud", action="instance.terminate",
                              resource=instance_id, ok=ok)
    return {"ok": ok}
