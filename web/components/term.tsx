"use client";
import * as Tooltip from "@radix-ui/react-tooltip";
import { GLOSSARY } from "@/lib/glossary";

/**
 * Inline glossary term: dotted-underline trigger that reveals a short
 * definition on hover/focus. Falls back to plain text for unknown ids.
 * Usage: <Term id="invariant">invariant</Term>
 */
export function Term({
  id,
  children,
}: {
  id: string;
  children?: React.ReactNode;
}) {
  const entry = GLOSSARY[id];
  const label = children ?? entry?.term ?? id;
  if (!entry) return <>{label}</>;
  return (
    <Tooltip.Provider delayDuration={150}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <button
            type="button"
            aria-label={`${entry.term}: ${entry.short}`}
            className="cursor-help border-b border-dotted border-muted text-inherit underline-offset-2 hover:border-accent focus-visible:outline focus-visible:outline-1 focus-visible:outline-accent"
          >
            {label}
          </button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side="top"
            sideOffset={6}
            className="z-50 max-w-xs rounded border border-border bg-panel-2 px-2.5 py-1.5 text-xs text-fg shadow-lg"
          >
            <span className="font-semibold text-accent">{entry.term}</span>
            <span className="mt-0.5 block text-muted">{entry.short}</span>
            <Tooltip.Arrow className="fill-border" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
