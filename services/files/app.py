"""Files service (port 8001) — HTTP surface over FileStore.

    GET    /files?path=      read
    DELETE /files?path=      delete
    POST   /files/rename     {path, dest}
"""

from __future__ import annotations

from fastapi import Query, Request

from dvah.services.memory import FileStore
from services.common.app_factory import create_service

store = FileStore()
app = create_service("files", lambda seed: store.reset(seed.get("files", {})))


@app.get("/files")
def read(path: str = Query(...)) -> dict:
    if not store.exists(path):
        return {"ok": False}
    return {"ok": True, "contents": store.read(path)}


@app.delete("/files")
def delete(path: str = Query(...)) -> dict:
    ok = store.delete(path)
    app.state.recorder.record(namespace="files", action="delete", resource=path, ok=ok)
    return {"ok": ok}


@app.post("/files/rename")
async def rename(request: Request) -> dict:
    body = await request.json()
    ok = store.rename(body["path"], body["dest"])
    app.state.recorder.record(namespace="files", action="rename", resource=body["path"],
                              dest=body["dest"], ok=ok)
    return {"ok": ok}
