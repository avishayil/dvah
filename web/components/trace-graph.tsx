import { cn } from "./ui/utils";
import type { TraceEvent, TraceResult } from "@/lib/types";
import { AlertTriangle, ArrowDown } from "lucide-react";

const KIND_COLOR: Record<string, string> = {
  "policy.decision": "text-info",
  executed: "text-allow",
  denied: "text-deny",
  delegate: "text-accent",
  "context.compiled": "text-warn",
  "provenance.recorded": "text-muted",
  "envelope.built": "text-muted",
};

function shortHash(h: string | null): string {
  return h ? h.replace("sha256:", "").slice(0, 10) : "—";
}

function eventLabel(e: TraceEvent): string {
  const d = e.detail ?? {};
  if (e.kind === "policy.decision")
    return `${d.verdict ?? "?"}${d.invariant ? ` [${d.invariant}]` : ""} — ${d.reason ?? ""}`;
  if (e.kind === "executed" || e.kind === "envelope.built")
    return `${d.namespace ?? "?"}.${d.action ?? "?"}${d.resource ? ` ${d.resource}` : ""}`;
  if (e.kind === "delegate") return `${d.child ?? ""} ${JSON.stringify(d.child_caps ?? [])}`;
  if (e.kind === "context.compiled")
    return d.untrusted_instruction ? "UNTRUSTED DATA IN INSTRUCTION CHANNEL" : "clean";
  if (e.kind === "provenance.recorded") return `sources=${JSON.stringify(d.sources ?? [])}`;
  if (e.kind === "denied") return String(d.invariant ?? "");
  return "";
}

/**
 * The signature security-trace flow graph: events top-to-bottom with the broken
 * invariant highlighted. Custom flex/SVG, no graph library.
 */
function violationNote(kind: string): string | null {
  // Each highlight names the specific invariant it violates (not a hardcoded INV-01).
  if (kind === "executed") return "executed without execution-time authorization (INV-01)";
  if (kind === "context.compiled") return "untrusted data promoted to the instruction channel (INV-06)";
  return null;
}

export function TraceGraph({ trace }: { trace: TraceResult }) {
  const unauthorized = new Set(trace.summary.unauthorized_executions);
  return (
    <div data-testid="trace-graph" className="mono text-xs">
      <p className="mb-2 text-muted">
        What the agent actually did, step by step —{" "}
        <span className="text-deny">red</span> marks where a security rule broke.
      </p>
      <div className="mb-2 rounded border border-border bg-panel-2 px-2 py-1 text-muted">
        user → plan → policy → execution
      </div>
      <details className="mb-2 rounded border border-border bg-panel px-2 py-1">
        <summary className="cursor-pointer text-muted">legend</summary>
        <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
          {Object.entries(KIND_COLOR).map(([kind, color]) => (
            <li key={kind} className="flex items-center gap-1">
              <span className={cn("font-semibold", color)}>●</span> {kind}
            </li>
          ))}
          <li className="flex items-center gap-1 text-deny">
            <AlertTriangle size={11} aria-hidden="true" /> invariant violation
          </li>
        </ul>
      </details>
      <ol className="space-y-1">
        {trace.events.map((e, i) => {
          const violation =
            (e.kind === "executed" && unauthorized.has(e.action_hash ?? "")) ||
            (e.kind === "context.compiled" && Boolean(e.detail?.untrusted_instruction));
          return (
            <li key={i} className="flex items-start gap-2">
              <span className="w-4 pt-0.5 text-muted">
                {i > 0 && <ArrowDown size={12} />}
              </span>
              <div
                data-violation={violation ? "true" : undefined}
                className={cn(
                  "flex-1 rounded border px-2 py-1",
                  violation
                    ? "border-deny/60 bg-deny/10"
                    : "border-border bg-panel",
                )}
              >
                <span className={cn("font-semibold", KIND_COLOR[e.kind] ?? "text-fg")}>
                  {e.kind}
                </span>{" "}
                <span className="text-muted">{shortHash(e.action_hash)}</span>{" "}
                <span>{eventLabel(e)}</span>
                {violation && violationNote(e.kind) && (
                  <div className="mt-0.5 flex items-center gap-1 text-deny">
                    <AlertTriangle size={12} /> {violationNote(e.kind)}
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      <div className="mt-3 space-y-1">
        {trace.summary.unauthorized_executions.length > 0 && (
          <div className="text-deny">
            ⚠ INV-01: {trace.summary.unauthorized_executions.length} action(s) executed
            without execution-time authorization.
          </div>
        )}
        {trace.summary.untrusted_instruction && (
          <div className="text-deny">
            ⚠ INV-06: untrusted data reached the instruction channel.
          </div>
        )}
        {trace.summary.denials.map((d, i) => (
          <div key={i} className="text-warn">
            ✗ denied {shortHash(d.action_hash)} [{d.invariant}]
          </div>
        ))}
        {trace.summary.unauthorized_executions.length === 0 &&
          !trace.summary.untrusted_instruction &&
          trace.summary.denials.length === 0 && (
            <div className="text-allow">no invariant violations observed.</div>
          )}
      </div>
    </div>
  );
}
