"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RunMode } from "@/lib/types";

// Run mode is a SINGLE global choice made in Settings (not per-lab). The workspace only
// REFLECTS it here:
//   • deterministic (default) — the reproducible, key-free security oracle; the exploit/
//     patch/prove buttons do all the grading. Nothing extra to do.
//   • live — when a model key is configured, a "Run with live model" button appears
//     (opt-in, billable) and shows the agent timeline + the two scores.
// Replay stays a CLI-only path (`dvah replay …`).

interface RunModeBadgeProps {
  onLiveRun?: () => void | Promise<void>;
  busy?: boolean;
}

export function RunModeBadge({ onLiveRun, busy = false }: RunModeBadgeProps) {
  const [mode, setMode] = useState<RunMode | null>(null);
  const [keyReady, setKeyReady] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api
      .getSettings()
      .then((s) => {
        if (cancelled) return;
        setMode(s.run_mode);
        setKeyReady(s.model.key_set || Object.values(s.env_keys ?? {}).some(Boolean));
      })
      .catch(() => !cancelled && setMode("deterministic"));
    return () => {
      cancelled = true;
    };
  }, []);

  if (mode === null) return null; // still resolving; avoid a flash

  const badge =
    "whitespace-nowrap rounded border px-1.5 py-0.5 text-[11px] border-border text-muted";
  const liveActionable = mode === "live" && keyReady && !!onLiveRun;

  return (
    <div
      role="group"
      aria-label="Run mode"
      data-testid="run-mode"
      data-mode={mode}
      className="flex flex-wrap items-center gap-2 text-[11px] text-muted"
    >
      <span className={badge} title="How lab agent runs execute — change it in Settings.">
        Mode: <span className="text-fg">{mode === "live" ? "Live" : "Deterministic"}</span>
      </span>

      {mode === "deterministic" && (
        <span className="text-muted">the exploit/patch/prove buttons do the grading — no key needed</span>
      )}

      {liveActionable && (
        <button
          type="button"
          data-live-run="true"
          disabled={busy}
          onClick={() => onLiveRun?.()}
          title="Run this lab through a real model (uses your Settings key; billable)."
          className="whitespace-nowrap rounded border border-accent/60 bg-accent/10 px-1.5 py-0.5 text-accent hover:brightness-110 disabled:opacity-60"
        >
          {busy ? "running…" : "Run with live model"}
        </button>
      )}

      {mode === "live" && !keyReady && (
        <span>
          set a model key in{" "}
          <Link href="/settings" className="text-accent hover:underline">
            Settings
          </Link>
        </span>
      )}

      <Link href="/settings" className="text-accent hover:underline" data-testid="run-mode-settings-link">
        change in Settings
      </Link>
    </div>
  );
}
