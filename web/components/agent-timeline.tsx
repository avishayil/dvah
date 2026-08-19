import { cn } from "./ui/utils";
import type { TraceEvent, TraceResult } from "@/lib/types";

// The agent-loop lanes, in reading order. Each trace event kind maps to exactly one lane
// so the run reads as: the model proposes → the harness authorizes → a tool runs → an
// observation returns. Security kinds land in Policy/Approval; tool I/O in Tool; the
// external-boundary trust downgrade in MCP.
export type Lane = "Model" | "Skill" | "MCP" | "Policy" | "Approval" | "Tool";

export const LANES: Lane[] = ["Model", "Skill", "MCP", "Policy", "Approval", "Tool"];

const KIND_LANE: Record<string, Lane> = {
  "user.task": "Model",
  "model.request": "Model",
  "model.response": "Model",
  "tool.proposed": "Model",
  "model.fallback": "Model",
  "subagent.started": "Model",
  delegate: "Model",
  "agent.finished": "Model",
  "skill.loaded": "Skill",
  "boundary.trust_downgraded": "MCP",
  "context.compiled": "Policy",
  "policy.decision": "Policy",
  denied: "Policy",
  "approval.used": "Approval",
  "envelope.built": "Tool",
  executed: "Tool",
  "observation.received": "Tool",
  "provenance.recorded": "Tool",
};

/** The lane a trace event belongs to (defaults to Model for unknown/agent-level events). */
export function laneFor(kind: string): Lane {
  return KIND_LANE[kind] ?? "Model";
}

const LANE_COLOR: Record<Lane, string> = {
  Model: "text-accent",
  Skill: "text-info",
  MCP: "text-warn",
  Policy: "text-info",
  Approval: "text-warn",
  Tool: "text-allow",
};

function label(e: TraceEvent): string {
  const d = e.detail ?? {};
  if (e.kind === "user.task") return String(d.task ?? d.prompt ?? "task");
  if (e.kind === "tool.proposed" || e.kind === "executed" || e.kind === "envelope.built")
    return `${d.namespace ?? "?"}.${d.action ?? "?"}${d.resource ? ` ${d.resource}` : ""}`;
  if (e.kind === "policy.decision")
    return `${d.verdict ?? "?"}${d.invariant ? ` [${d.invariant}]` : ""}`;
  if (e.kind === "denied") return `denied [${d.invariant ?? "?"}]`;
  if (e.kind === "skill.loaded") return `${d.name ?? "skill"}${d.version ? `@${d.version}` : ""}`;
  if (e.kind === "subagent.started") return String(d.child ?? "subagent");
  if (e.kind === "model.fallback") return `fallback → ${d.to ?? "?"}`;
  if (e.kind === "boundary.trust_downgraded") return "external output → untrusted";
  return "";
}

/**
 * The agent-loop timeline: every trace event placed in its lane (Model / Skill / MCP /
 * Policy / Approval / Tool), in order — so you can watch the model propose and the harness
 * decide. Complements the security-focused TraceGraph.
 */
export function AgentTimeline({ trace }: { trace: TraceResult }) {
  const events = trace.events ?? [];
  return (
    <div data-testid="agent-timeline" className="mono text-xs">
      <p className="mb-2 text-muted">
        The agent loop, lane by lane — the model proposes, the harness decides, a tool runs.
      </p>
      <ul aria-label="Timeline lanes" className="mb-2 flex flex-wrap gap-x-3 gap-y-0.5">
        {LANES.map((l) => (
          <li key={l} className="flex items-center gap-1">
            <span className={cn("font-semibold", LANE_COLOR[l])}>●</span> {l}
          </li>
        ))}
      </ul>
      <ol className="space-y-1">
        {events.map((e, i) => {
          const lane = laneFor(e.kind);
          return (
            <li key={i} data-lane={lane} className="flex items-start gap-2">
              <span
                className={cn(
                  "w-16 shrink-0 pt-1 text-right font-semibold uppercase tracking-wide",
                  LANE_COLOR[lane],
                )}
              >
                {lane}
              </span>
              <div className="flex-1 rounded border border-border bg-panel px-2 py-1">
                <span className="text-fg">{e.kind}</span>{" "}
                <span className="text-muted">{label(e)}</span>
              </div>
            </li>
          );
        })}
        {events.length === 0 && <li className="text-muted">no timeline events yet.</li>}
      </ol>
    </div>
  );
}
