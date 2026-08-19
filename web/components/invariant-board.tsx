import { Check, X, Circle } from "lucide-react";
import { cn } from "./ui/utils";
import { INVARIANT_MAP } from "@/lib/invariants";

export type InvariantCell = { id: string; holds: boolean | null };

/**
 * The Invariant Status Board — chips that flip ✓/✗ as tests run. `holds === null`
 * means "not yet evaluated". Pure/presentational so it is trivially testable.
 */
export function InvariantBoard({
  cells,
  title = "Invariants",
}: {
  cells: InvariantCell[];
  title?: string;
}) {
  const STATE_LABEL = { hold: "holds", broken: "broken", pending: "not yet evaluated" };
  return (
    <div>
      <div id="invariant-board-title" className="mb-2 text-xs uppercase tracking-wide text-muted">
        {title}
      </div>
      <ul
        role="list"
        aria-labelledby="invariant-board-title"
        aria-live="polite"
        aria-atomic="true"
        className="flex flex-wrap gap-1.5"
      >
        {cells.map((c) => {
          const state = c.holds === null ? "pending" : c.holds ? "hold" : "broken";
          return (
            <li key={c.id} role="listitem">
              <span
                title={INVARIANT_MAP[c.id] ?? c.id}
                data-state={state}
                className={cn(
                  "state-flip inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-xs mono",
                  // Solid text + stronger backgrounds to clear WCAG AA on the dark panel.
                  state === "hold" && "border-allow bg-allow/20 text-allow",
                  state === "broken" && "border-deny bg-deny/20 text-deny",
                  state === "pending" && "border-border bg-panel-2 text-fg",
                )}
              >
                {state === "hold" && <Check size={12} aria-hidden="true" />}
                {state === "broken" && <X size={12} aria-hidden="true" />}
                {state === "pending" && <Circle size={12} aria-hidden="true" />}
                {c.id}
                <span className="sr-only"> — {STATE_LABEL[state]}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
