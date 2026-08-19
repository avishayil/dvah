"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Pause, Play, ChevronLeft, ChevronRight, X, Sparkles } from "lucide-react";
import { Button } from "./ui/button";

// A hands-off, narrated auto-solve demo. Each step shows a caption and (optionally) runs a
// deterministic action against the live workspace (run the exploit, apply the reference
// fix, re-run to green). The security run is real — the deterministic oracle, no model.
export type DemoStep = {
  caption: string;
  // Optional side-effecting action performed when the step becomes active going FORWARD.
  // Kept idempotent so replaying a step is harmless.
  run?: () => Promise<void> | void;
};

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// Controller: sequences steps, runs the current step's action, and (when playing and
// motion is allowed) auto-advances after each action settles. Exposed for unit testing.
export function useGuidedDemo(steps: DemoStep[], opts?: { dwellMs?: number; auto?: boolean }) {
  const dwellMs = opts?.dwellMs ?? 3200;
  const reduced = typeof opts?.auto === "boolean" ? !opts.auto : prefersReducedMotion();
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(!reduced);
  const [busy, setBusy] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stepsRef = useRef(steps);
  stepsRef.current = steps;

  const clearTimer = () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
  };

  // Move to step `i`; run its action when advancing forward. Returns when the action settles.
  const go = useCallback(async (i: number, runAction: boolean) => {
    const list = stepsRef.current;
    if (i < 0 || i >= list.length) return;
    clearTimer();
    setIndex(i);
    if (runAction && list[i]?.run) {
      setBusy(true);
      try {
        await list[i].run!();
      } finally {
        setBusy(false);
      }
    }
  }, []);

  const next = useCallback(() => {
    setIndex((i) => Math.min(i + 1, stepsRef.current.length - 1));
  }, []);
  const prev = useCallback(() => {
    clearTimer();
    setPlaying(false);
    setIndex((i) => Math.max(i - 1, 0));
  }, []);
  const toggle = useCallback(() => setPlaying((p) => !p), []);

  // Drive: whenever the active index changes, run its action; if playing, schedule the next.
  const lastRun = useRef(-1);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const runAction = index > lastRun.current; // only run each action once, going forward
      lastRun.current = Math.max(lastRun.current, index);
      const step = stepsRef.current[index];
      if (runAction && step?.run) {
        setBusy(true);
        try {
          await step.run();
        } finally {
          if (!cancelled) setBusy(false);
        }
      }
      if (cancelled) return;
      if (playing && index < stepsRef.current.length - 1) {
        timer.current = setTimeout(() => setIndex((i) => Math.min(i + 1, stepsRef.current.length - 1)), dwellMs);
      }
    })();
    return () => {
      cancelled = true;
      clearTimer();
    };
  }, [index, playing, dwellMs]);

  useEffect(() => () => clearTimer(), []);

  return { index, playing, busy, total: steps.length, next, prev, toggle, go };
}

// Convenience wrapper: mount this only once the session is ready. It owns the controller
// and renders the overlay. Kept separate from the hook so the hook stays unit-testable.
export function GuidedDemoRunner({
  steps,
  onClose,
  auto,
}: {
  steps: DemoStep[];
  onClose: () => void;
  auto?: boolean;
}) {
  const ctl = useGuidedDemo(steps, { auto });
  return (
    <GuidedDemoOverlay
      steps={steps}
      index={ctl.index}
      playing={ctl.playing}
      busy={ctl.busy}
      total={ctl.total}
      onNext={ctl.next}
      onPrev={ctl.prev}
      onToggle={ctl.toggle}
      onClose={onClose}
    />
  );
}

export function GuidedDemoOverlay({
  steps,
  index,
  playing,
  busy,
  total,
  onNext,
  onPrev,
  onToggle,
  onClose,
}: {
  steps: DemoStep[];
  index: number;
  playing: boolean;
  busy: boolean;
  total: number;
  onNext: () => void;
  onPrev: () => void;
  onToggle: () => void;
  onClose: () => void;
}) {
  const step = steps[index];
  if (!step) return null;
  const atEnd = index >= total - 1;
  return (
    <div
      role="region"
      aria-label="Guided demo"
      data-testid="guided-demo"
      className="pointer-events-auto fixed inset-x-0 bottom-0 z-40 mx-auto max-w-3xl p-4"
    >
      <div className="soft-card rounded-2xl border border-accent/50 bg-panel/95 p-4 shadow-lg backdrop-blur">
        <div className="flex items-center gap-2">
          <Sparkles size={15} className="text-accent" />
          <span className="mono text-[11px] uppercase tracking-wide text-accent">
            Guided demo · DVAH-001
          </span>
          <span className="mono text-[11px] text-muted">
            {index + 1}/{total}
          </span>
          {busy && <span className="text-[11px] text-muted">running…</span>}
          <button
            onClick={onClose}
            aria-label="Close the guided demo"
            className="ml-auto rounded px-1 text-muted hover:text-fg"
          >
            <X size={15} />
          </button>
        </div>
        <p className="mt-2 text-sm text-fg" data-testid="guided-demo-caption">
          {step.caption}
        </p>
        <div className="mt-3 flex items-center gap-2">
          <Button size="sm" onClick={onPrev} disabled={index === 0} aria-label="Previous step">
            <ChevronLeft size={14} /> Back
          </Button>
          <Button size="sm" onClick={onToggle} aria-label={playing ? "Pause the demo" : "Play the demo"}>
            {playing ? <Pause size={14} /> : <Play size={14} />}
            {playing ? "Pause" : "Play"}
          </Button>
          {atEnd ? (
            <Button size="sm" variant="primary" onClick={onClose} aria-label="Finish the demo">
              Done — explore it yourself
            </Button>
          ) : (
            <Button size="sm" onClick={onNext} disabled={busy} aria-label="Next step">
              Next <ChevronRight size={14} />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
