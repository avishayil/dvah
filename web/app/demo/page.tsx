"use client";
import * as React from "react";
import Link from "next/link";
import { GuidedDemoPlayer, type DemoFrame } from "@/components/guided-demo-player";

// Full-screen, cursor-driven guided demo of DVAH-001. Renders over the app chrome
// (fixed inset-0 in the player) and is reached from the landing's "Start with DVAH-001".
export default function DemoPage() {
  const [frames, setFrames] = React.useState<DemoFrame[] | null>(null);
  const [error, setError] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    fetch("/demo/manifest.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("no manifest"))))
      .then((f) => !cancelled && setFrames(f as DemoFrame[]))
      .catch(() => !cancelled && setError(true));
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="mx-auto max-w-xl p-8 text-center text-sm text-muted">
        The guided demo isn&apos;t available.{" "}
        <Link href="/labs/DVAH-001-plan-time-authorization?mode=learn&demo=1" className="text-accent hover:underline">
          Open DVAH-001 →
        </Link>
      </div>
    );
  }
  if (!frames) {
    return <div className="fixed inset-0 z-[100] grid place-items-center bg-black text-sm text-muted">Loading the guided demo…</div>;
  }
  return <GuidedDemoPlayer frames={frames} />;
}
