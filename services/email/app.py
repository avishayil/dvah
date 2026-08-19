"""Email service (port 8003) — in-memory outbox.

    POST /email/send    {to, subject, body}   -> records to outbox
    GET  /email/outbox                         -> list sent messages
"""

from __future__ import annotations

from fastapi import Request

from services.common.app_factory import create_service


class Outbox:
    def __init__(self) -> None:
        self._messages: list[dict] = []

    def reset(self, _seed: dict) -> None:
        self._messages = []

    def send(self, message: dict) -> int:
        self._messages.append(message)
        return len(self._messages)

    @property
    def messages(self) -> list[dict]:
        return list(self._messages)


store = Outbox()
app = create_service("email", store.reset)


@app.post("/email/send")
async def send(request: Request) -> dict:
    body = await request.json()
    message_id = store.send(
        {"to": body.get("to", ""), "subject": body.get("subject", ""),
         "body": body.get("body", "")}
    )
    app.state.recorder.record(namespace="email", action="send",
                              resource=body.get("to", ""), ok=True)
    return {"ok": True, "id": message_id}


@app.get("/email/outbox")
def outbox() -> dict:
    return {"outbox": store.messages}
