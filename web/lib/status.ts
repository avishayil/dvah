// Lab progress is derived client-side from run outcomes and persisted locally.
export type LabStatus = "not-started" | "exploited" | "patched" | "proven";

const KEY = "dvah:status:v1";
const LEGACY_KEYS = ["dvah:status"];

export function loadStatuses(): Record<string, LabStatus> {
  if (typeof window === "undefined") return {};
  try {
    const current = window.localStorage.getItem(KEY);
    if (current) return JSON.parse(current);
    // One-time migration from any older key.
    for (const legacy of LEGACY_KEYS) {
      const old = window.localStorage.getItem(legacy);
      if (old) {
        window.localStorage.setItem(KEY, old);
        window.localStorage.removeItem(legacy);
        return JSON.parse(old);
      }
    }
    return {};
  } catch {
    return {};
  }
}

export function setStatus(id: string, status: LabStatus): void {
  if (typeof window === "undefined") return;
  const all = loadStatuses();
  all[id] = status;
  window.localStorage.setItem(KEY, JSON.stringify(all));
}

const RANK: Record<LabStatus, number> = {
  "not-started": 0,
  exploited: 1,
  patched: 2,
  proven: 3,
};

/** Never regress a lab's status to a lower rank. */
export function mergeStatus(current: LabStatus | undefined, next: LabStatus): LabStatus {
  if (!current) return next;
  return RANK[next] >= RANK[current] ? next : current;
}
