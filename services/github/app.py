"""GitHub service (port 8002) — HTTP surface over GithubStore.

Repos contain slashes (``repo/acme/payments``) so ``repo`` travels as a query param
rather than a path segment.

    GET    /github/issues?repo=       list issues
    POST   /github/comment            {repo, issue, body}
    DELETE /github/repo?repo=         delete repository
"""

from __future__ import annotations

from fastapi import Query, Request

from dvah.services.memory import GithubStore
from services.common.app_factory import create_service

store = GithubStore()
app = create_service("github", lambda seed: store.reset(seed.get("github", {})))


@app.get("/github/issues")
def list_issues(repo: str = Query(...)) -> dict:
    return {"ok": True, "issues": store.list_issues(repo)}


@app.post("/github/comment")
async def comment(request: Request) -> dict:
    body = await request.json()
    ok = store.comment(repo=body["repo"], issue=int(body.get("issue", 0)),
                       body=str(body.get("body", "")))
    app.state.recorder.record(namespace="github", action="issue.comment",
                              resource=body["repo"], issue=int(body.get("issue", 0)), ok=ok)
    return {"ok": ok}


@app.delete("/github/repo")
def delete_repo(repo: str = Query(...)) -> dict:
    ok = store.delete_repository(repo)
    app.state.recorder.record(namespace="github", action="repository.delete", resource=repo, ok=ok)
    return {"ok": ok}
