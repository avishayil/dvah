"use client";
import * as React from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Home, Pause, Play, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

// A full-screen, cursor-driven "video" of DVAH-001. Each frame is a REAL 2×-DSF screenshot of
// the workspace (see e2e/capture-demo.spec.ts). Every slide plays three ~3s beats:
//   1) FULL   — the whole workspace, no zoom (opens un-zoomed every slide)
//   2) ZOOM   — a smooth camera push-in to the slide's `focus` region (moderate)
//   3) CLICK  — the pointer glides to the on-frame control and clicks
// then auto-advances to the next slide (back to beat 1). Frames come from public/demo/manifest.json.
export type DemoRect = { xPct: number; yPct: number; wPct: number; hPct: number };
export type DemoFrame = {
  image: string;
  caption: string;
  cursor: { xPct: number; yPct: number } | null;
  focus?: DemoRect | null;
  click: boolean;
  dwellMs: number;
};

const LAB_HREF = "/labs/DVAH-001-plan-time-authorization?mode=learn&demo=1";

// Beat durations (ms). Tunable — the user asked for ~3s each.
const BEAT_FULL_MS = 3000;
const BEAT_ZOOM_MS = 3000;
const BEAT_CLICK_MS = 3000;
const ZOOM_MS = 1200; // the zoom-in transition itself (within beat 2)
const GLIDE_MS = 850; // the cursor glide (within beat 3)

// Moderate zoom: fill ~82% of the stage with the focus region, capped so it's never a tight
// crop. transform-origin top-left → the math is a plain `p*S + T`.
const MAX_ZOOM = 1.7;
const FILL = 82;
type Phase = "full" | "zoom" | "click";

function zoomTransform(focus?: DemoRect | null): { transform: string; scale: number } {
  if (!focus || focus.wPct <= 0) return { transform: "none", scale: 1 };
  const scale = Math.max(1, Math.min(MAX_ZOOM, FILL / focus.wPct));
  const fcx = focus.xPct + focus.wPct / 2;
  // clamp the pan so the scaled frame [t, t+100S] always covers the stage [0,100]
  const cover = (v: number) => Math.max(100 - 100 * scale, Math.min(0, v));
  const tx = cover(50 - fcx * scale);
  // top-align: the workspace columns are top-heavy (board/controls up top, empty below),
  // so anchor near the top of the focus region rather than its vertical center.
  const ty = cover(2 - focus.yPct * scale);
  return { transform: `translate(${tx.toFixed(2)}%, ${ty.toFixed(2)}%) scale(${scale.toFixed(3)})`, scale };
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = React.useState(false);
  React.useEffect(() => {
    const m = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(m.matches);
    const on = () => setReduced(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return reduced;
}

export function GuidedDemoPlayer({ frames }: { frames: DemoFrame[] }) {
  const reduced = usePrefersReducedMotion();
  const [i, setI] = React.useState(0);
  const [phase, setPhase] = React.useState<Phase>("full");
  const [playing, setPlaying] = React.useState(!reduced);
  const [arrived, setArrived] = React.useState(false); // cursor reached target (→ ripple)
  const last = frames.length - 1;
  const frame = frames[i];
  const atEnd = i === last;

  const go = React.useCallback(
    (n: number) => {
      const clamped = Math.max(0, Math.min(frames.length - 1, n));
      setI(clamped);
      setPhase("full");
      setArrived(false);
    },
    [frames.length],
  );

  // Beat state machine: full → zoom → click → (advance). Paused when !playing.
  React.useEffect(() => {
    if (!playing) return;
    if (reduced) return; // reduced-motion: hold on the final (zoomed) state; use prev/next.
    if (phase === "full") {
      const t = setTimeout(() => setPhase("zoom"), BEAT_FULL_MS);
      return () => clearTimeout(t);
    }
    if (phase === "zoom") {
      const t = setTimeout(() => setPhase("click"), BEAT_ZOOM_MS);
      return () => clearTimeout(t);
    }
    // click beat: glide → ripple → advance (unless last slide, where we stop)
    const glide = setTimeout(() => setArrived(true), GLIDE_MS);
    const next = setTimeout(() => {
      if (!atEnd) go(i + 1);
      else setPlaying(false);
    }, BEAT_CLICK_MS);
    return () => {
      clearTimeout(glide);
      clearTimeout(next);
    };
  }, [playing, reduced, phase, i, atEnd, go]);

  // Keyboard: space=play/pause, arrows=step.
  React.useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if (e.key === " ") {
        e.preventDefault();
        setPlaying((p) => !p);
      } else if (e.key === "ArrowRight") go(i + 1);
      else if (e.key === "ArrowLeft") go(i - 1);
    };
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, [i, go]);

  if (!frames.length) return null;

  // Beat 1 = full frame (identity). Beats 2/3 (and reduced-motion) = zoomed to focus.
  const zoomed = reduced || phase !== "full";
  const fx = zoomTransform(frame?.focus);
  const layerTransform = zoomed ? fx.transform : "none";
  const layerScale = zoomed ? fx.scale : 1;
  // Cursor: parked at the focus center during zoom, glides to the target during click.
  const showCursor = !!frame?.cursor && (phase === "click" || (reduced && frame.click));
  const target = frame?.cursor ?? { xPct: 50, yPct: 50 };

  return (
    <div data-testid="demo-player" className="fixed inset-0 z-[100] flex flex-col bg-black text-fg">
      {/* top bar */}
      <div className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
        <span className="mono text-xs text-accent">Guided demo · DVAH-001 — exploit → fix → prove</span>
        <Link href="/" className="flex items-center gap-1 text-muted hover:text-fg">
          <Home size={14} /> Home
        </Link>
      </div>

      {/* stage */}
      <div className="flex min-h-0 flex-1 items-center justify-center px-4">
        <div className="relative mx-auto aspect-video w-full max-w-[min(96vw,1500px)] max-h-[76vh] overflow-hidden rounded-lg border border-border bg-bg shadow-2xl">
          <div
            data-testid="demo-zoom"
            data-phase={phase}
            className="absolute inset-0"
            style={{
              transform: layerTransform,
              transformOrigin: "0 0",
              transition: reduced ? "none" : `transform ${ZOOM_MS}ms cubic-bezier(0.22,0.61,0.36,1)`,
              willChange: "transform",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              key={frame.image}
              src={`/demo/${frame.image}`}
              alt={frame.caption}
              className="absolute inset-0 h-full w-full object-contain"
            />
            {showCursor && (
              <div
                data-testid="demo-cursor"
                aria-hidden="true"
                className="pointer-events-none absolute z-10"
                style={{
                  left: `${target.xPct}%`,
                  top: `${target.yPct}%`,
                  transform: `translate(-8%, -8%) scale(${(1 / layerScale).toFixed(3)})`,
                  transition: reduced ? "none" : `left ${GLIDE_MS}ms ease, top ${GLIDE_MS}ms ease`,
                }}
              >
                {arrived && frame.click && (
                  <span className="absolute -left-3 -top-3 h-8 w-8 animate-ping rounded-full bg-accent/60" />
                )}
                <svg width="26" height="26" viewBox="0 0 24 24" className="drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">
                  <path d="M4 2l6 15 2.5-6.5L19 8z" fill="#fff" stroke="#04262a" strokeWidth="1.2" />
                </svg>
              </div>
            )}
          </div>
          {/* beat indicator */}
          <div className="absolute bottom-2 right-3 z-20 mono text-[10px] text-muted/80">
            {phase === "full" ? "overview" : phase === "zoom" ? "zoom in" : "action"}
          </div>
        </div>
      </div>

      {/* caption + controls */}
      <div className="mx-auto w-full max-w-4xl px-4 pb-4">
        <p data-testid="demo-caption" className="min-h-[3.25rem] text-center text-sm leading-relaxed text-muted">
          <span className="mono mr-2 text-xs text-accent">
            {i + 1}/{frames.length}
          </span>
          {frame.caption}
        </p>
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          <Button variant="default" aria-label={playing ? "Pause" : "Play"} onClick={() => setPlaying((p) => !p)}>
            {playing ? <Pause size={14} /> : <Play size={14} />} {playing ? "Pause" : "Play"}
          </Button>
          <Button variant="default" aria-label="Previous step" onClick={() => go(i - 1)} disabled={i === 0}>
            <ArrowLeft size={14} /> Back
          </Button>
          <Button variant="default" aria-label="Next step" onClick={() => go(i + 1)} disabled={atEnd}>
            Next <ArrowRight size={14} />
          </Button>
          <Button variant="default" aria-label="Restart" onClick={() => { go(0); setPlaying(!reduced); }}>
            <RotateCcw size={14} /> Restart
          </Button>
          <div className="ml-1 flex gap-1" aria-hidden="true">
            {frames.map((_, n) => (
              <span key={n} className={`h-1.5 w-1.5 rounded-full ${n === i ? "bg-accent" : "bg-border"}`} />
            ))}
          </div>
          {atEnd && (
            <Link href={LAB_HREF} data-testid="open-dvah-001" className="ml-2">
              <Button variant="primary">
                Open DVAH-001 <ArrowRight size={14} />
              </Button>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
