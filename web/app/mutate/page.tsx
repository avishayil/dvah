"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { InvariantBoard, type InvariantCell } from "@/components/invariant-board";
import type { MutateResult } from "@/lib/types";

export default function MutatePage() {
  const [seed, setSeed] = useState(0);
  const [count, setCount] = useState(2);
  const [reveal, setReveal] = useState(false);
  const [result, setResult] = useState<MutateResult | null>(null);
  const [running, setRunning] = useState(false);

  async function run() {
    setRunning(true);
    try {
      setResult(await api.mutate(seed, count, reveal));
    } finally {
      setRunning(false);
    }
  }

  const cells: InvariantCell[] =
    result?.per.map((p) => ({ id: p.id, holds: p.holds })) ?? [];

  return (
    <div className="mx-auto max-w-2xl p-6">
      <Link href="/concepts" className="text-xs text-accent hover:underline">
        ← Learn
      </Link>
      <h1 className="mt-1 text-xl font-semibold">Chaos mode</h1>
      <p className="mt-2 text-sm text-muted">
        A lab hands you one broken rule to fix. Chaos mode does the opposite: it secretly
        sabotages the runtime — breaking a hidden set of the 12 security invariants at
        once — and asks you to work out <span className="text-fg">which</span> ones broke.
        You don&apos;t edit any code here; it&apos;s a diagnosis drill for whether you can
        read the invariant board and name the failure.
      </p>
      <ol className="mt-3 space-y-1 text-sm text-muted">
        <li>
          <span className="text-fg">1.</span> Pick a <span className="mono">seed</span>{" "}
          (any number — the same seed always breaks the same invariants) and{" "}
          <span className="mono">count</span> (how many to break).
        </li>
        <li>
          <span className="text-fg">2.</span> Run it and read the board — each ✗ is an
          invariant that no longer holds.
        </li>
        <li>
          <span className="text-fg">3.</span> Predict which broke, then tick{" "}
          <span className="mono">reveal</span> to check your answer.
        </li>
      </ol>
      <p className="mt-2 text-xs text-muted">
        Same idea as the <span className="mono">conformance suite</span>, but run against a
        deliberately-broken harness instead of a real one.
      </p>

      <div className="mb-4 mt-5 flex items-end gap-3 text-xs">
        <label className="flex flex-col gap-1">
          seed
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(Number(e.target.value))}
            className="w-20 rounded border border-border bg-panel-2 px-2 py-1 mono"
          />
        </label>
        <label className="flex flex-col gap-1">
          count
          <input
            type="number"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-20 rounded border border-border bg-panel-2 px-2 py-1 mono"
          />
        </label>
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={reveal} onChange={(e) => setReveal(e.target.checked)} />
          reveal
        </label>
        <Button size="sm" variant="primary" onClick={run} disabled={running}>
          mutate
        </Button>
      </div>

      {result && (
        <div className="space-y-3">
          <InvariantBoard cells={cells} title="Invariant battery" />
          <div className="text-sm">
            Result:{" "}
            <span className={result.holding === result.total ? "text-allow" : "text-deny"}>
              {result.holding} / {result.total} invariants hold
            </span>
          </div>
          {result.revealed && (
            <div className="text-xs text-warn">
              revealed defeats: {result.revealed.join(", ") || "(none)"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
