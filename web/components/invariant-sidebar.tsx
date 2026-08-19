"use client";
import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { INVARIANTS } from "@/lib/invariants";
import { cn } from "./ui/utils";

export function InvariantSidebar() {
  const [open, setOpen] = useState(true);
  return (
    <aside className="w-72 shrink-0 border-l border-border bg-panel p-3">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls="invariant-reference-list"
        className="flex w-full items-center gap-1 text-xs uppercase tracking-wide text-muted"
      >
        <ChevronRight
          size={12}
          aria-hidden="true"
          className={cn("transition-transform", open && "rotate-90")}
        />
        Invariant reference
      </button>
      {open && (
        <ul id="invariant-reference-list" className="mt-2 space-y-2">
          {INVARIANTS.map((i) => (
            <li key={i.id} className="text-xs">
              <span className="mono text-accent">{i.id}</span>
              <p className="text-muted">{i.statement}</p>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
