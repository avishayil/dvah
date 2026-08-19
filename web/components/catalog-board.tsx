import Link from "next/link";
import { Badge } from "./ui/badge";
import { cn } from "./ui/utils";
import type { ChallengeSummary } from "@/lib/types";
import type { LabStatus } from "@/lib/status";

const STATUS_STYLE: Record<LabStatus, string> = {
  "not-started": "border-border text-muted",
  exploited: "border-warn/50 bg-warn/10 text-warn",
  patched: "border-info/50 bg-info/10 text-info",
  proven: "border-allow/50 bg-allow/10 text-allow",
};

const DIFF_STYLE: Record<string, string> = {
  easy: "border-allow/50 text-allow",
  medium: "border-warn/50 text-warn",
  hard: "border-deny/50 text-deny",
};

export function CatalogBoard({
  challenges,
  statuses,
  mode,
}: {
  challenges: ChallengeSummary[];
  statuses: Record<string, LabStatus>;
  mode: "learn" | "ctf";
}) {
  // Beginner → advanced (backend sorts too; belt-and-suspenders for older payloads).
  const ordered = [...challenges].sort((a, b) => (a.order ?? 999) - (b.order ?? 999));
  return (
    <table className="w-full border-collapse text-sm" data-tour="lab-table">
      <thead>
        <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted">
          <th className="py-2 pr-3 font-medium">ID</th>
          <th className="py-2 pr-3 font-medium">Lab · what you&apos;ll learn</th>
          <th className="py-2 pr-3 font-medium">Level</th>
          <th className="py-2 pr-3 font-medium">Invariants</th>
          <th className="py-2 pr-3 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {ordered.map((c) => {
          const status = statuses[c.id] ?? "not-started";
          const href = `/labs/${c.id}?mode=${mode}`;
          return (
            <tr key={c.id} className="border-b border-border/60 hover:bg-panel-2">
              <td className="py-2 pr-3 align-top mono text-accent">
                <Link href={href}>{c.id}</Link>
              </td>
              <td className="py-2 pr-3 align-top">
                <Link href={href} className="font-medium hover:underline">
                  {c.title}
                </Link>
                <p className="text-xs text-muted">
                  {c.teaches ?? c.objective}
                  {c.estimated_minutes ? ` · ~${c.estimated_minutes} min` : ""}
                </p>
              </td>
              <td className="py-2 pr-3 align-top">
                <span
                  className={cn(
                    "inline-block rounded border px-1.5 py-0.5 text-xs",
                    DIFF_STYLE[c.difficulty] ?? "border-border text-muted",
                  )}
                >
                  {c.difficulty || "?"}
                </span>
              </td>
              <td className="py-2 pr-3 align-top">
                <div className="flex flex-wrap gap-1">
                  {c.invariants.map((inv) => (
                    <Badge key={inv} className="text-accent">
                      {inv}
                    </Badge>
                  ))}
                </div>
              </td>
              <td className="py-2 pr-3 align-top">
                <span
                  className={cn(
                    "inline-block rounded border px-1.5 py-0.5 text-xs",
                    STATUS_STYLE[status],
                  )}
                >
                  {status}
                </span>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
