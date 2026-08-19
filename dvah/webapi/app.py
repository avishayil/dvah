"""FastAPI application for the DVAH lab UI.

Wires the shared catalog, ephemeral sessions, the sandboxed runner, the trace endpoint,
tiered hints/solution reveal, the mutation engine, and the optional AI tutor.
"""

from __future__ import annotations

import asyncio
import os

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from . import catalog, hints, runner, settings, tutor
from .schemas import (
    CreateSessionRequest,
    LiveRunRequest,
    MutateRequest,
    PutFileRequest,
    RunRequest,
    SettingsUpdate,
    TraceRequest,
    TutorRequest,
)
from .sessions import SessionManager

app = FastAPI(title="DVAH", version="0.1.0")

# Origins allowed to call the API from a browser. Default "*" for local dev; the
# Docker Compose stack pins it to the web origin via DVAH_CORS_ORIGINS.
_CORS_ORIGINS = [o.strip() for o in os.environ.get("DVAH_CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS = SessionManager()
_RUNNER = runner.get_runner()


def _session_or_404(session_id: str):
    try:
        return SESSIONS.path(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown session") from exc


def _grade(session_id: str, path, markers: list[str], task_id: str | None) -> dict:
    """Run the suite for a session. Isolated (assessment) sessions grade out of band in a
    throwaway workspace so the hidden tests/solution never touch the learner's tree;
    inprocess (self-study) sessions run the copied suite in place."""
    if SESSIONS.isolated:
        # Opt-in fullest split: grade the invariant battery across a process boundary, where
        # the learner's code runs with no tests/ or solution/ present. Off by default because
        # it returns a per-invariant verdict (the security oracle), not the per-tier report the
        # UI renders; the assembly path stays the default so the API shape is unchanged.
        if os.environ.get("DVAH_GRADER") == "rpc":
            from ..grading import grade_rpc

            return grade_rpc(
                SESSIONS.challenge_id(session_id),
                code_dir=SESSIONS.code_dir(session_id),
            )
        from ..grading import grade

        return grade(
            SESSIONS.challenge_id(session_id),
            code_dir=SESSIONS.code_dir(session_id),
            markers=markers,
            task_id=task_id,
        )
    return _RUNNER.run(path, markers, task_id)


def _reject_if_ctf(session_id: str | None) -> None:
    """In CTF mode, hints + solution are locked (enforces the session's declared mode;
    adequate for local single-user — not an anti-cheat)."""
    if session_id and SESSIONS.mode(session_id) == "ctf":
        raise HTTPException(status_code=403, detail="hints and solution are locked in CTF mode")


# --- catalog ----------------------------------------------------------------
@app.get("/api/challenges")
def list_challenges():
    return catalog.list_challenges()


@app.get("/api/challenges/{challenge_id}")
def get_challenge(challenge_id: str):
    try:
        return catalog.briefing(challenge_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- sessions ---------------------------------------------------------------
@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    try:
        return SESSIONS.create(req.challenge_id, req.mode)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}/files")
def get_files(session_id: str):
    _session_or_404(session_id)
    return {
        "files": SESSIONS.files(session_id),
        "readonly_files": SESSIONS.readonly_files(session_id),
    }


@app.put("/api/sessions/{session_id}/files")
def put_file(session_id: str, req: PutFileRequest):
    _session_or_404(session_id)
    try:
        SESSIONS.write_file(session_id, req.path, req.contents)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/sessions/{session_id}/run")
async def run_session(session_id: str, req: RunRequest):
    # Off the event loop: the runner blocks on a pytest subprocess.
    path = _session_or_404(session_id)
    result = await asyncio.to_thread(_grade, session_id, path, req.markers, req.task_id)
    SESSIONS.record_run(session_id, result)  # progress log + tutor context
    return result


@app.post("/api/sessions/{session_id}/trace")
async def trace_session(session_id: str, req: TraceRequest):
    path = _session_or_404(session_id)
    result = await asyncio.to_thread(_run_trace, path, req.task_id, req.solution)
    SESSIONS.record_trace(session_id, result.get("summary", {}))
    return result


@app.post("/api/sessions/{session_id}/live-run")
async def live_run_session(session_id: str, req: LiveRunRequest):
    """Run the lab through a REAL model (opt-in, billable), using the Settings key.

    Key-gated: 400 unless a key is configured for the resolved provider. Returns the same
    agent-timeline + dual-score shape as the deterministic trace, so the UI reuses its
    renderers. The deterministic model stays the default/CI oracle; this only runs on an
    explicit user request and never in CI."""
    from ..providers.profiles import resolve_profile

    path = _session_or_404(session_id)
    selection = req.model or settings.SETTINGS.tutor_provider()
    provider, _model_id = resolve_profile(selection, dict(os.environ))
    if provider != "deterministic" and settings.SETTINGS.api_key(provider) is None:
        raise HTTPException(
            status_code=400,
            detail=f"configure a {provider} model key in Settings to run live",
        )
    result = await asyncio.to_thread(_run_live, path, req.task_id, selection)
    SESSIONS.record_trace(session_id, result.get("summary", {}))
    return result


@app.post("/api/sessions/{session_id}/reset")
def reset_session(session_id: str):
    _session_or_404(session_id)
    return {
        "editable_files": SESSIONS.reset(session_id),
        "readonly_files": SESSIONS.readonly_files(session_id),
    }


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    _session_or_404(session_id)
    SESSIONS.cleanup(session_id)
    return {"ok": True}


@app.get("/api/sessions/{session_id}/progress")
def session_progress(session_id: str):
    _session_or_404(session_id)
    return SESSIONS.progress(session_id)


@app.websocket("/api/sessions/{session_id}/stream")
async def stream_run(websocket: WebSocket, session_id: str):
    # Reject unknown sessions before accepting (don't silently swallow later).
    try:
        SESSIONS.path(session_id)
    except KeyError:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        payload = await websocket.receive_json()
        try:
            req = RunRequest(**payload)
        except ValidationError:
            await websocket.send_json({"type": "error", "message": "invalid run request"})
            return
        path = SESSIONS.path(session_id)
        await websocket.send_json({"type": "log", "message": "running…"})
        result = await asyncio.to_thread(_grade, session_id, path, req.markers, req.task_id)
        for test in result["tests"]:
            await websocket.send_json({"type": "test", **test})
        await websocket.send_json({"type": "done", "result": result})
    except (WebSocketDisconnect, KeyError):
        return
    finally:
        await websocket.close()


# --- trace helper -----------------------------------------------------------
def _run_trace(session_dir, task_id: str, use_solution: bool) -> dict:
    from ..observability.render import summarize_trace
    from ..scenarios.loader import load_challenge

    loaded = load_challenge(session_dir, use_solution=use_solution)
    halted = None
    try:
        loaded.harness.run_task(loaded.root_ctx, task_id)
    except Exception as exc:  # a denial legitimately halts the trace
        halted = {"error": str(exc)}
    events = [
        {"kind": e.kind, "task_id": e.task_id, "action_hash": e.action_hash, "detail": e.detail}
        for e in loaded.trace.events
    ]
    from ..scoring import as_dict, dual_score

    resp = {
        "events": events,
        "summary": summarize_trace(loaded.trace).model_dump(),
        # Additive: the two independent scores for the 7b UI. Runtime Security is the
        # model-independent complete-mediation verdict; Live Agent Exercise summarizes
        # what happened on this run.
        "dual_score": as_dict(dual_score(loaded.trace)),
        "live_experience": loaded.live_experience,
    }
    if halted:
        resp["halted"] = halted
    return resp


def _run_live(session_dir, task_id: str, selection: str) -> dict:
    """Drive the lab through a live ModelSession (built from the Settings key) and return
    the agent-timeline + dual score. Falls back to the deterministic oracle if the live
    provider errors (missing SDK/bad key) — emitting a ``model.fallback`` event — so this
    never hard-fails a run."""
    from ..observability.render import summarize_trace
    from ..providers.model import AgentState
    from ..providers.router_model import build_model_session
    from ..scenarios.loader import load_challenge
    from ..scoring import as_dict, dual_score

    loaded = load_challenge(session_dir, use_solution=False)
    prompt = loaded.task_prompt(task_id)
    session = build_model_session(
        selection,
        deterministic_provider=loaded.harness.cfg.model,
        task_id=task_id,
        prompt=prompt,
        trace=loaded.trace,
        get_key=settings.SETTINGS.api_key,
    )
    halted = None
    try:
        loaded.harness.run_session(
            loaded.root_ctx, session, AgentState(task_id=task_id), prompt=prompt
        )
    except Exception as exc:  # a denial legitimately halts the trace
        halted = {"error": str(exc)}
    events = [
        {"kind": e.kind, "task_id": e.task_id, "action_hash": e.action_hash, "detail": e.detail}
        for e in loaded.trace.events
    ]
    resp = {
        "events": events,
        "summary": summarize_trace(loaded.trace).model_dump(),
        "dual_score": as_dict(dual_score(loaded.trace)),
        "live_experience": loaded.live_experience,
        "model": selection,
    }
    if halted:
        resp["halted"] = halted
    return resp


# --- hints / walkthrough / solution ----------------------------------------
@app.get("/api/challenges/{challenge_id}/hints")
def get_hints(challenge_id: str, session_id: str | None = None):
    _reject_if_ctf(session_id)
    try:
        return hints.hint_index(challenge_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/challenges/{challenge_id}/hints/{tier_index}")
def get_hint_tier(challenge_id: str, tier_index: int, session_id: str | None = None):
    _reject_if_ctf(session_id)
    try:
        tier = hints.hint_tier(challenge_id, tier_index)
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="no such hint tier") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if session_id:
        SESSIONS.record_hint(session_id, tier_index)
    return tier


@app.get("/api/challenges/{challenge_id}/walkthrough")
def get_walkthrough(challenge_id: str):
    return {"steps": hints.walkthrough_steps(challenge_id)}


@app.get("/api/challenges/{challenge_id}/solution")
def get_solution(challenge_id: str, session_id: str | None = None):
    _reject_if_ctf(session_id)
    try:
        return hints.solution(challenge_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --- mutation engine --------------------------------------------------------
@app.post("/api/mutate")
def mutate(req: MutateRequest):
    from ..mutation.engine import choose_flags, run

    flags = choose_flags(req.seed, req.count)
    result = run(flags)
    resp = {
        "holding": result.holding,
        "total": result.total,
        "per": [{"id": inv, "holds": ok} for inv, ok in result.holds.items()],
    }
    if req.reveal:
        resp["revealed"] = flags.active()
    return resp


# --- settings ---------------------------------------------------------------
@app.get("/api/settings")
def get_settings():
    return settings.view()


@app.put("/api/settings")
def update_settings(req: SettingsUpdate):
    try:
        settings.SETTINGS.update(
            tutor_enabled=req.tutor_enabled,
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
            run_mode=req.run_mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return settings.view()


@app.post("/api/settings/tutor/test")
def test_tutor():
    """Make a minimal real call to verify the tutor credentials/provider work.

    Always returns 200 with ``{ok, ...}`` — a failed provider/auth call is a normal,
    actionable outcome (the UI shows the real error), not a gateway/server error. This is
    why it no longer raises 502."""
    if not tutor.is_enabled():
        return {"ok": False, "error": "tutor not enabled or missing credentials"}
    try:
        reply = tutor.coach({}, [], {}, "Reply with the single word: ready.")
        return {"ok": True, "reply": (reply or "").strip()[:200]}
    except Exception as exc:  # surface the real provider/auth error text to the UI
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


# --- optional AI tutor ------------------------------------------------------
@app.post("/api/tutor")
def ask_tutor(req: TutorRequest):
    if not tutor.is_enabled():
        raise HTTPException(status_code=503, detail="tutor disabled")
    _session_or_404(req.session_id)
    code = {f["path"]: f["contents"] for f in SESSIONS.files(req.session_id)}
    reply = tutor.coach(
        code,
        failing=SESSIONS.last_failing(req.session_id),
        trace_summary=SESSIONS.last_trace_summary(req.session_id),
        question=req.question,
    )
    return {"reply": reply}
