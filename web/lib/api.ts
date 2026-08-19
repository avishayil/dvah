import type {
  ChallengeDetail,
  ChallengeSummary,
  Hint,
  HintsIndex,
  MutateResult,
  RunResult,
  Session,
  SessionProgress,
  SettingsUpdate,
  SettingsView,
  SolutionReveal,
  TraceResult,
  Walkthrough,
} from "./types";

export const DEFAULT_API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const API_BASE_KEY = "dvah.apiBase";

/** Resolve the API base at call time so a Settings override takes effect live. */
export function getApiBase(): string {
  if (typeof window !== "undefined") {
    const override = window.localStorage.getItem(API_BASE_KEY);
    if (override) return override;
  }
  return DEFAULT_API_BASE;
}

/** Persist a runtime API base override (empty string clears it). */
export function setApiBase(value: string): void {
  if (typeof window === "undefined") return;
  if (value.trim()) window.localStorage.setItem(API_BASE_KEY, value.trim());
  else window.localStorage.removeItem(API_BASE_KEY);
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export { ApiError };

function _sid(sessionId?: string): string {
  return sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
}

export const api = {
  listChallenges: () =>
    req<{ challenges: ChallengeSummary[] }>("/api/challenges"),
  getChallenge: (id: string) => req<ChallengeDetail>(`/api/challenges/${id}`),
  createSession: (challenge_id: string, mode: "learn" | "ctf" = "learn") =>
    req<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ challenge_id, mode }),
    }),
  putFile: (sid: string, path: string, contents: string) =>
    req<{ ok: true }>(`/api/sessions/${sid}/files`, {
      method: "PUT",
      body: JSON.stringify({ path, contents }),
    }),
  run: (sid: string, markers: string[], task_id?: string) =>
    req<RunResult>(`/api/sessions/${sid}/run`, {
      method: "POST",
      body: JSON.stringify({ markers, task_id }),
    }),
  trace: (sid: string, task_id: string, solution = false) =>
    req<TraceResult>(`/api/sessions/${sid}/trace`, {
      method: "POST",
      body: JSON.stringify({ task_id, solution }),
    }),
  // Opt-in, billable: run the lab through a real model (uses the Settings key). `model`
  // may be a provider or profile; "" → the configured tutor provider. Returns the same
  // agent-timeline + dual-score shape as `trace`.
  liveRun: (sid: string, task_id: string, model = "") =>
    req<TraceResult>(`/api/sessions/${sid}/live-run`, {
      method: "POST",
      body: JSON.stringify({ task_id, model }),
    }),
  reset: (sid: string) =>
    req<Session>(`/api/sessions/${sid}/reset`, { method: "POST" }),
  hintsIndex: (id: string, sessionId?: string) =>
    req<HintsIndex>(`/api/challenges/${id}/hints${_sid(sessionId)}`),
  hint: (id: string, tier: number, sessionId?: string) =>
    req<Hint>(`/api/challenges/${id}/hints/${tier}${_sid(sessionId)}`),
  walkthrough: (id: string) =>
    req<Walkthrough>(`/api/challenges/${id}/walkthrough`),
  solution: (id: string, sessionId?: string) =>
    req<SolutionReveal>(`/api/challenges/${id}/solution${_sid(sessionId)}`),
  progress: (sid: string) => req<SessionProgress>(`/api/sessions/${sid}/progress`),
  mutate: (seed?: number, count?: number, reveal?: boolean) =>
    req<MutateResult>("/api/mutate", {
      method: "POST",
      body: JSON.stringify({ seed, count, reveal }),
    }),
  tutor: (session_id: string, question?: string) =>
    req<{ reply: string }>("/api/tutor", {
      method: "POST",
      body: JSON.stringify({ session_id, question }),
    }),
  getSettings: () => req<SettingsView>("/api/settings"),
  putSettings: (patch: SettingsUpdate) =>
    req<SettingsView>("/api/settings", {
      method: "PUT",
      body: JSON.stringify(patch),
    }),
  testTutor: () =>
    req<{ ok: boolean; reply?: string; error?: string }>("/api/settings/tutor/test", {
      method: "POST",
    }),
};

/** WebSocket URL for streamed run output. */
export function streamUrl(sid: string): string {
  const base = getApiBase().replace(/^http/, "ws");
  return `${base}/api/sessions/${sid}/stream`;
}
