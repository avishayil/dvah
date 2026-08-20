"use client";
import { Check, X, AlertCircle, AlertTriangle, Play } from "lucide-react";
import { Button } from "./ui/button";
import { cn } from "./ui/utils";
import type { RunResult, TestResult } from "@/lib/types";

const MARKERS = ["functional", "exploit", "invariant", "adversarial"] as const;

const MARKER_HELP: Record<string, string> = {
  functional: "Does the agent still do its normal job after your fix?",
  exploit: "The attack itself — red until you fix the bug.",
  invariant: "The safety rule must hold for ALL inputs, not just the demo.",
  adversarial: "Variations of the attack, so a too-narrow fix doesn't sneak through.",
};

// A failing security test (exploit/invariant/adversarial) before you patch is the GOAL,
// not an error — it means the attack still works. Only a failing `functional` test is a
// real regression.
function isExpectedFail(t: TestResult): boolean {
  return t.outcome === "failed" && t.marker !== "functional";
}

function OutcomeIcon({ test }: { test: TestResult }) {
  if (test.outcome === "passed") return <Check size={13} className="text-allow" />;
  if (test.outcome === "error") return <AlertCircle size={13} className="text-warn" />;
  if (isExpectedFail(test)) return <AlertTriangle size={13} className="text-warn" />;
  return <X size={13} className="text-deny" />; // failed functional = real regression
}

function Summary({ result }: { result: RunResult }) {
  const tests = result.tests;
  if (tests.length === 0) return null;
  const failing = tests.filter((t) => t.outcome !== "passed");
  const functionalBroken = failing.some((t) => t.marker === "functional");

  if (failing.length === 0) {
    return (
      <div className="rounded border border-allow/40 bg-allow/10 p-2 text-xs text-allow">
        ✓ Fixed — the invariant holds and every test passes.
      </div>
    );
  }
  if (functionalBroken) {
    return (
      <div className="rounded border border-deny/40 bg-deny/10 p-2 text-xs text-deny">
        A legitimate task broke — your change altered normal behavior. Check the failing
        functional test.
      </div>
    );
  }
  return (
    <div className="rounded border border-warn/40 bg-warn/10 p-2 text-xs text-warn">
      ⚠ Vulnerability reproduced — the attack still works. This is expected before you
      patch: open the <span className="text-fg">Trace</span> tab to see why, fix the code in{" "}
      <span className="mono">guardrails/vulnerable/</span>, then re-run until this turns green.
    </div>
  );
}

export function RunPanel({
  onRun,
  running,
  result,
  logLines,
}: {
  onRun: (markers: string[]) => void;
  running: boolean;
  result: RunResult | null;
  logLines: string[];
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5" data-tour="run-markers">
        {MARKERS.map((m) => (
          <Button
            key={m}
            size="sm"
            variant={m === "exploit" ? "primary" : "default"}
            disabled={running}
            title={MARKER_HELP[m]}
            onClick={() => onRun([m])}
          >
            <Play size={12} /> {m}
          </Button>
        ))}
        <Button
          size="sm"
          disabled={running}
          title="Run all markers: functional, exploit, invariant, adversarial"
          aria-label="Run all four test markers"
          onClick={() => onRun([...MARKERS])}
        >
          run all
        </Button>
      </div>

      {!result && !running && (
        <div className="rounded border border-border bg-panel-2 p-2 text-xs text-muted">
          <p className="mb-1 text-fg">How this works</p>
          <p>
            Run <span className="text-accent">exploit</span> first — it should{" "}
            <span className="text-warn">fail</span>: that confirms the bug is live. Patch the
            code in <span className="mono">guardrails/vulnerable/</span>, then re-run{" "}
            <span className="text-accent">invariant</span> and{" "}
            <span className="text-accent">adversarial</span> — your fix must make them{" "}
            <span className="text-allow">pass (green)</span> for <em>all</em> inputs, not just
            the demo. <span className="text-accent">functional</span> confirms legit tasks
            still work.
          </p>
        </div>
      )}

      {/* Live progress only while running — never the final view, so runs render alike. */}
      {running && (
        <pre className="max-h-40 overflow-auto rounded border border-border bg-panel-2 p-2 text-xs mono">
          {logLines.length ? logLines.map((l, i) => <div key={i}>{l}</div>) : "running…"}
        </pre>
      )}

      {result && !running && (
        <>
          <Summary result={result} />
          <ul className="space-y-1 text-xs">
            {result.tests.map((t, i) => (
              <li
                key={i}
                className={cn(
                  "flex min-w-0 items-center gap-2 rounded border px-2 py-1",
                  t.outcome === "passed" && "border-allow/30",
                  t.outcome === "error" && "border-warn/40",
                  isExpectedFail(t) && "border-warn/40",
                  t.outcome === "failed" && t.marker === "functional" && "border-deny/40",
                )}
              >
                <span className="shrink-0">
                  <OutcomeIcon test={t} />
                </span>
                <span className="min-w-0 flex-1 truncate mono" title={t.name.split("::").pop()}>
                  {t.name.split("::").pop()}
                </span>
                <span className="ml-auto shrink-0 rounded border border-border px-1 text-[10px] text-muted mono">
                  {t.marker ?? "—"}
                </span>
              </li>
            ))}
          </ul>
          {result.stdout && (
            <details className="rounded border border-border bg-panel-2 text-xs">
              <summary className="cursor-pointer px-2 py-1 text-muted">Raw pytest output</summary>
              <pre className="max-h-56 overflow-auto px-2 pb-2 mono">{result.stdout}</pre>
            </details>
          )}
        </>
      )}
    </div>
  );
}
