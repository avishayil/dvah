"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { ChevronDown, ChevronRight, Lock, RotateCcw } from "lucide-react";
import { Button } from "./ui/button";
import { cn } from "./ui/utils";
import type { EditableFile, EditableFileGroup } from "@/lib/types";

const Monaco = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => <div className="p-3 text-xs text-muted mono">loading editor…</div>,
});

const isReadonly = (f: EditableFile) => f.writable === false;
const langFor = (path: string) => (/\.ya?ml$/.test(path) ? "yaml" : "python");
const groupOf = (f: EditableFile): EditableFileGroup => f.group ?? "patch";
const labelOf = (f: EditableFile) => f.label ?? f.path;

// The three tab clusters, in order. Each read-only group carries a short "why it's here".
const GROUPS: { id: EditableFileGroup; label: string; hint: string }[] = [
  { id: "patch", label: "Patch this", hint: "editable runtime file — you patch this" },
  { id: "world", label: "The world · read-only", hint: "environment the runtime runs against — read-only" },
  { id: "reference", label: "Harness reference · read-only", hint: "harness module your code calls into — read-only" },
];

export function EditorPanel({
  files,
  onChange,
  onReset,
}: {
  files: EditableFile[];
  onChange: (path: string, contents: string) => void;
  onReset: () => void;
}) {
  const [active, setActive] = useState(files[0]?.path ?? "");
  // The harness-reference group is collapsed by default so the file you patch stays front-and-center.
  const [showRef, setShowRef] = useState(false);

  const byGroup = (g: EditableFileGroup) => files.filter((f) => groupOf(f) === g);
  const hasRef = byGroup("reference").length > 0;
  // Reference tabs only render when expanded; anything else is always visible.
  const visible = files.filter((f) => groupOf(f) !== "reference" || showRef);

  // Keep the active tab valid: if it vanished (e.g. collapsing the reference group while a
  // reference tab was active, or files changing on reset), fall back to the first file.
  useEffect(() => {
    if (!visible.some((f) => f.path === active)) setActive(visible[0]?.path ?? files[0]?.path ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showRef, files]);

  const current = files.find((f) => f.path === active) ?? files[0];
  const readonly = current ? isReadonly(current) : false;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border bg-panel px-2">
        {/* tablist wraps ONLY tab buttons + aria-hidden group labels (a11y: role=tablist's
            interactive children must be role=tab; the Reset/Reference toggle stay outside). */}
        <div
          role="tablist"
          aria-label="Session files"
          data-tour="editor-tabs"
          className="flex items-center gap-1 overflow-x-auto"
        >
          {GROUPS.map((grp) => {
            const groupFiles = byGroup(grp.id).filter((f) => grp.id !== "reference" || showRef);
            if (groupFiles.length === 0) return null;
            return (
              <div key={grp.id} className="flex items-center gap-1">
                <span
                  aria-hidden="true"
                  className="ml-1 shrink-0 whitespace-nowrap border-l border-border pl-2 text-[10px] uppercase tracking-wide text-muted first:border-l-0 first:pl-0"
                >
                  {grp.label}
                </span>
                {groupFiles.map((f) => {
                  const ro = isReadonly(f);
                  const selected = f.path === current?.path;
                  return (
                    <button
                      key={f.path}
                      role="tab"
                      aria-selected={selected}
                      aria-label={`${labelOf(f)} — ${grp.hint}`}
                      title={grp.hint}
                      onClick={() => setActive(f.path)}
                      className={cn(
                        "flex items-center gap-1 whitespace-nowrap border-b-2 px-2 py-1.5 text-xs mono transition-colors",
                        selected
                          ? ro
                            ? "border-muted text-fg"
                            : "border-accent text-fg"
                          : "border-transparent text-muted hover:text-fg",
                      )}
                    >
                      {ro && <Lock size={11} className="opacity-70" aria-hidden />}
                      {labelOf(f)}
                    </button>
                  );
                })}
              </div>
            );
          })}
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-1">
          {hasRef && (
            <Button
              size="sm"
              variant="ghost"
              aria-expanded={showRef}
              aria-label="Toggle harness reference files"
              onClick={() => setShowRef((v) => !v)}
            >
              {showRef ? <ChevronDown size={12} /> : <ChevronRight size={12} />} Reference files
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={onReset}>
            <RotateCcw size={12} /> reset
          </Button>
        </div>
      </div>
      <div className="border-b border-border bg-panel-2 px-3 py-1 text-[11px] text-muted">
        You edit the <span className="text-accent">accent</span> tab. The{" "}
        <Lock size={10} className="mb-0.5 inline opacity-70" aria-hidden /> lock-badged tabs are
        read-only context — the world the runtime runs against and the harness your code calls into.
      </div>
      <div className="min-h-0 flex-1">
        {current && (
          <Monaco
            height="100%"
            theme="vs-dark"
            language={langFor(current.path)}
            path={current.path}
            value={current.contents}
            onMount={(_editor, monaco) => {
              // Expose the monaco instance so e2e tests can set the buffer value
              // (which fires onChange → updates state → the app persists it on run).
              (window as unknown as { monaco?: unknown }).monaco = monaco;
            }}
            onChange={(v) => !readonly && onChange(current.path, v ?? "")}
            options={{
              readOnly: readonly,
              fontSize: 13,
              minimap: { enabled: false },
              scrollBeyondLastLine: false,
              fontFamily: "var(--font-mono)",
              automaticLayout: true,
            }}
          />
        )}
      </div>
    </div>
  );
}
