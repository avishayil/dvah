"use client";
import { useCallback, useEffect } from "react";
import { driver, type DriveStep } from "driver.js";
import "driver.js/dist/driver.css";
import { Compass } from "lucide-react";
import { Button } from "./ui/button";

export type TourStep = { el: string; title: string; text: string };

/**
 * A dependency-light interactive product tour (driver.js). Auto-starts once per
 * `tourKey` on first visit (localStorage-gated), and renders a "Take the tour" button
 * to replay. SSR-safe (guards `window`) and respects prefers-reduced-motion.
 */
export function Tour({
  tourKey,
  steps,
  autostart = true,
  label = "Tour",
}: {
  tourKey: string;
  steps: TourStep[];
  autostart?: boolean;
  label?: string;
}) {
  const start = useCallback(() => {
    if (typeof document === "undefined") return;
    const present = steps.filter((s) => document.querySelector(s.el));
    if (present.length === 0) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const driveSteps: DriveStep[] = present.map((s) => ({
      element: s.el,
      popover: { title: s.title, description: s.text },
    }));
    driver({
      animate: !reduce,
      showProgress: true,
      steps: driveSteps,
      nextBtnText: "Next",
      prevBtnText: "Back",
      doneBtnText: "Done",
    }).drive();
  }, [steps]);

  useEffect(() => {
    if (!autostart || typeof window === "undefined") return;
    const key = `dvah:tour:${tourKey}:v1`;
    // Defensive: some environments expose no localStorage — never crash over it.
    let seen = true;
    try {
      seen = Boolean(window.localStorage?.getItem(key));
    } catch {
      seen = false;
    }
    if (seen) return;

    // Poll until the step anchors have mounted, THEN mark seen + start. Marking seen
    // before the targets exist (the old behavior) would silently burn the one-shot
    // auto-start when the workspace mounts slower than a fixed delay.
    let timer: ReturnType<typeof setTimeout>;
    let tries = 0;
    const tick = () => {
      const present = steps.some((s) => document.querySelector(s.el));
      if (!present && tries++ < 25) {
        timer = setTimeout(tick, 200);
        return;
      }
      try {
        window.localStorage?.setItem(key, "seen");
      } catch {
        /* storage unavailable — tour just won't be gated */
      }
      start();
    };
    timer = setTimeout(tick, 300);
    return () => clearTimeout(timer);
  }, [autostart, tourKey, start, steps]);

  return (
    <Button
      size="sm"
      variant="ghost"
      onClick={start}
      title="Take the guided tour"
      aria-label="Take the guided tour"
      className="shrink-0 whitespace-nowrap"
    >
      <Compass size={14} /> {label}
    </Button>
  );
}
