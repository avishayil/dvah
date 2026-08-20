"use client";
import { use, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { HelpCircle } from "lucide-react";
import { api } from "@/lib/api";
import { BriefingPanel } from "@/components/briefing-panel";
import { EditorPanel } from "@/components/editor-panel";
import { RunPanel } from "@/components/run-panel";
import { InvariantBoard, type InvariantCell } from "@/components/invariant-board";
import { TraceGraph } from "@/components/trace-graph";
import { AgentTimeline } from "@/components/agent-timeline";
import { DualScorePanel } from "@/components/dual-score";
import { RunModeBadge } from "@/components/run-mode";
import { GuidedDemoRunner, type DemoStep } from "@/components/guided-demo";
import { HelpDrawer } from "@/components/help-drawer";
import { Tour, type TourStep } from "@/components/tour";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { loadStatuses, mergeStatus, setStatus, type LabStatus } from "@/lib/status";
import type { EditableFile, RunResult, Session, TraceResult } from "@/lib/types";

// Editable vulnerable file(s) first (group "patch"), then the read-only environment files
// (group "world"). The read-only harness-reference modules are merged in separately from the
// challenge detail (see referenceFiles below), since they don't live on the session.
function toEditorFiles(s: Session): EditableFile[] {
  const editable = s.editable_files.map(
    (f): EditableFile => ({ ...f, writable: f.writable ?? true, group: "patch" }),
  );
  const world = (s.readonly_files ?? []).map(
    (f): EditableFile => ({ ...f, writable: false, group: "world" }),
  );
  return [...editable, ...world];
}

// The harness modules the vulnerable code imports (dvah.harness.resolver, …) become read-only
// editor tabs so ALL read-only context lives in one place. `dvah.harness.resolver` →
// path `dvah/harness/resolver.py` (for python highlighting) with the dotted name as the label.
function referenceToFile(r: { module: string; contents: string }): EditableFile {
  return {
    path: `${r.module.replace(/\./g, "/")}.py`,
    contents: r.contents,
    writable: false,
    group: "reference",
    label: r.module,
  };
}

const WORKSPACE_TOUR: TourStep[] = [
  { el: '[data-tour="briefing"]', title: "1 · What you're fixing", text: "The goal, the security rule at stake, and the file you'll patch." },
  { el: '[data-tour="editor"]', title: "2 · The vulnerable code", text: "Edit this in place — this is the runtime bug you fix." },
  { el: '[data-tour="editor-tabs"]', title: "Main file vs. read-only context", text: "The accent tab is the runtime file you patch. The lock-badged tabs are read-only context, grouped: the world your runtime runs against (users, agents, resources, plans) and — under 'Reference files' — the harness modules your code calls into." },
  { el: '[data-tour="run"]', title: "3 · Run the exploit", text: "Run 'exploit' first — it should fail (red). That's the bug in action." },
  { el: '[data-tour="invariants"]', title: "The invariant board", text: "The safety rule at stake. It flips green when your fix holds for all inputs." },
  { el: '[data-tour="trace-tab"]', title: "See WHY it happened", text: "The trace shows what the agent actually did, step by step." },
  { el: '[data-tour="timeline-tab"]', title: "Agent timeline + two scores", text: "The agent loop in lanes — model, skill, MCP, policy, approval, tool — plus two independent scores: Runtime Security (does the harness hold?) and Live Agent Exercise (what the model did). A model avoiding the bait doesn't make the harness secure." },
  { el: '[data-tour="walkthrough"]', title: "Stuck?", text: "Tiered hints, a step-by-step guide, and — last resort — the full solution." },
];

export default function LabPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const sp = useSearchParams();
  const mode = (sp.get("mode") as "learn" | "ctf") ?? "learn";
  // The guided auto-solve demo is a learn-mode-only, deterministic walk-through.
  const demo = sp.get("demo") === "1" && mode !== "ctf";

  const { data: detail } = useQuery({
    queryKey: ["challenge", id],
    queryFn: () => api.getChallenge(id),
  });

  const [sid, setSid] = useState<string | null>(null);
  const [files, setFiles] = useState<EditableFile[]>([]);
  const [tasks, setTasks] = useState<string[]>([]);
  const [task, setTask] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    api.createSession(id, mode).then((s) => {
      if (cancelled) return;
      setSid(s.session_id);
      setFiles(toEditorFiles(s));
      setTasks(s.tasks);
      setTask(s.tasks.find((t) => t.includes("exploit")) ?? s.tasks[0] ?? "");
    });
    return () => {
      cancelled = true;
    };
  }, [id, mode]);

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [trace, setTrace] = useState<TraceResult | null>(null);
  const [helpOpen, setHelpOpen] = useState(false);
  const [tab, setTab] = useState<"run" | "trace" | "timeline">("run");
  const [showBanner, setShowBanner] = useState(false);
  useEffect(() => {
    if (typeof window !== "undefined")
      setShowBanner(!window.localStorage.getItem("dvah:loopbanner:dismissed"));
  }, []);
  function dismissBanner() {
    setShowBanner(false);
    if (typeof window !== "undefined")
      window.localStorage.setItem("dvah:loopbanner:dismissed", "1");
  }

  const invariantCells: InvariantCell[] = useMemo(() => {
    const ids = detail?.invariants.map((i) => i.id) ?? [];
    const per = new Map(result?.invariants.per.map((p) => [p.id, p.holds]));
    return ids.map((idv) => ({ id: idv, holds: per.has(idv) ? per.get(idv)! : null }));
  }, [detail, result]);

  // Editor tabs = the session's editable/world files + the read-only harness-reference
  // modules (from the challenge detail). Everything read-only lives in the editor now.
  const editorFiles: EditableFile[] = useMemo(
    () => [...files, ...(detail?.references ?? []).map(referenceToFile)],
    [files, detail],
  );

  function onEdit(path: string, contents: string) {
    setFiles((fs) => fs.map((f) => (f.path === path ? { ...f, contents } : f)));
  }

  async function saveAll() {
    if (!sid) return;
    // Only editable (guardrails/vulnerable/) files are persisted — environment tabs are read-only.
    const writable = files.filter((f) => f.writable !== false);
    await Promise.all(writable.map((f) => api.putFile(sid, f.path, f.contents)));
  }

  async function onRun(markers: string[], opts?: { save?: boolean }) {
    if (!sid) return;
    setRunning(true);
    setLogLines([]);
    setResult(null);

    // Never run against stale files: surface save failures instead of silently ignoring.
    // `save: false` is used when the caller has already persisted the files (e.g. the
    // guided demo applies + persists the reference fix), so we don't overwrite them.
    try {
      if (opts?.save !== false) await saveAll();
    } catch (e) {
      setLogLines([
        `Failed to save your changes: ${e instanceof Error ? e.message : "unknown error"}`,
      ]);
      setRunning(false);
      return;
    }

    try {
      // The run result is the single source of truth (RunPanel renders it, incl. raw
      // stdout in a collapsible), so repeated runs render identically. No WebSocket:
      // it added flaky "connection failed" console noise for no real benefit.
      const res = await api.run(sid, markers, task);
      setResult(res);

      const anyFailed = res.tests.some((t) => t.outcome !== "passed");
      const proven =
        res.tests.length > 0 &&
        !anyFailed &&
        res.invariants.holding === res.invariants.total;
      const exploitTests = res.tests.filter((t) => t.marker === "exploit");
      const exploitBlocked =
        exploitTests.length > 0 && exploitTests.every((t) => t.outcome === "passed");
      const next: LabStatus = proven ? "proven" : exploitBlocked ? "patched" : "exploited";
      setStatus(id, mergeStatus(loadStatuses()[id], next));

      // If the trace tab is open, refresh it to reflect the just-run code.
      if (tab === "trace") await loadTrace();
    } finally {
      setRunning(false);
    }
  }

  async function loadTrace() {
    if (!sid || !task) return;
    setTrace(await api.trace(sid, task));
  }

  const [liveBusy, setLiveBusy] = useState(false);
  // Opt-in live run: drive the lab through a real model (uses the Settings key) and show
  // the agent timeline + two scores. Falls back server-side to the deterministic oracle if
  // the provider errors; a 400 means no key is configured.
  async function runLive() {
    if (!sid || !task || liveBusy) return;
    setLiveBusy(true);
    try {
      const res = await api.liveRun(sid, task);
      setTrace(res);
      setTab("timeline");
    } catch (e) {
      setLogLines([
        `Live run unavailable: ${e instanceof Error ? e.message : "unknown error"}. Set a model key in Settings.`,
      ]);
      setTab("run");
    } finally {
      setLiveBusy(false);
    }
  }

  // ---- Guided auto-solve demo (learn-mode `?demo=1`) --------------------------------
  const [demoOpen, setDemoOpen] = useState(true);
  const { data: walk } = useQuery({
    queryKey: ["walkthrough", id],
    queryFn: () => api.walkthrough(id),
    enabled: demo,
  });

  // Overlay the reference fix onto the editable file(s), matched by basename
  // (guardrails/solution/executor.py → guardrails/vulnerable/executor.py). Deterministic, no model.
  async function applyDemoFix() {
    if (!sid) return;
    const sol = await api.solution(id, sid);
    const byName = new Map(sol.files.map((f) => [f.path.split("/").pop(), f.contents]));
    // The scenario loads the slot by the *vulnerable* class name (e.g. `PlanTimeExecutor`),
    // but the reference solution renames the class (e.g. `PerActionExecutor`). Copying it verbatim
    // would break the import, so rename the solution's class back to the original — this is the
    // same "keep the class name, fix the body" patch a learner makes.
    const className = (src: string) => src.match(/class\s+(\w+)/)?.[1];
    const next = files.map((f) => {
      if (f.writable === false) return f;
      const solSrc = byName.get(f.path.split("/").pop() ?? "");
      if (solSrc == null) return f;
      const orig = className(f.contents);
      const solName = className(solSrc);
      const fixed =
        orig && solName && orig !== solName ? solSrc.split(solName).join(orig) : solSrc;
      return { ...f, contents: fixed };
    });
    await Promise.all(
      next.filter((f) => f.writable !== false).map((f) => api.putFile(sid, f.path, f.contents)),
    );
    setFiles(next);
  }

  const demoSteps: DemoStep[] = useMemo(() => {
    const s = walk?.steps ?? [];
    const cap = (i: number, fallback: string) => s[i] ?? fallback;
    return [
      {
        caption:
          "Meet the harness — the layer that must authorize every action the moment it runs. DVAH-001's bug: it authorizes once, up front, then trusts that decision forever.",
      },
      {
        caption: cap(
          0,
          "Watch the exploit: the agent is allowed to read a file, but then deletes the prod database — an action never authorized at execution time. The board goes red (INV-01).",
        ),
        run: async () => {
          setTab("timeline");
          await onRun(["exploit", "invariant"]);
        },
      },
      {
        caption: cap(
          1,
          "Why it happened: authorization was bound to the plan, not to the resolved action. A plan is a proposal with no authority.",
        ),
      },
      {
        caption: cap(
          3,
          "The fix: route every step through the per-action gate so each resolved operation is authorized immediately before it executes. Applying the reference fix now…",
        ),
        run: applyDemoFix,
      },
      {
        caption:
          "Prove it: the exploit and its mutated variants (delete → rename) are all denied, and the invariant now holds for every input. The board turns green.",
        run: async () => {
          setTab("run");
          // The fix is already persisted by applyDemoFix; don't re-save (would overwrite).
          await onRun(["exploit", "invariant", "adversarial"], { save: false });
        },
      },
      {
        caption:
          "That's the harness doing its job: the model can propose anything, but only authorized actions execute. Explore the code and trace yourself, or try another lab.",
      },
    ];
    // onRun/applyDemoFix are stable-enough closures re-read via the controller each render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [walk, sid, id, task, files]);

  // Populate/refresh the trace whenever the Trace/Agent-timeline tab is shown or the task changes.
  useEffect(() => {
    if ((tab === "trace" || tab === "timeline") && sid && task) loadTrace();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, task, sid]);

  async function onReset() {
    if (!sid) return;
    const s = await api.reset(sid);
    setFiles(toEditorFiles(s));
    setResult(null);
  }

  if (!detail) return <p className="p-4 text-sm text-muted">loading challenge…</p>;

  return (
    <div className="flex h-full min-h-0 flex-col" data-session-id={sid ?? undefined}>
      {showBanner && (
        <div className="flex items-center gap-3 border-b border-border bg-panel-2 px-3 py-1.5 text-xs">
          <span className="text-muted">
            <span className="text-fg">The loop:</span> 1 Run{" "}
            <span className="text-accent">exploit</span> (red) → 2 open{" "}
            <span className="text-accent">Trace</span> to see why → 3 edit the file → 4
            re-run until the board is <span className="text-allow">green</span>.
          </span>
          <button
            onClick={dismissBanner}
            aria-label="Dismiss the loop guide"
            className="ml-auto rounded px-1 text-muted hover:text-fg"
          >
            ✕
          </button>
        </div>
      )}
      <div className="flex min-h-0 flex-1 flex-col lg:grid lg:grid-cols-[320px_1fr_420px]">
      {/* left: briefing */}
      <div data-tour="briefing" className="min-h-[220px] overflow-auto border-b border-border lg:min-h-0 lg:overflow-hidden lg:border-b-0 lg:border-r">
        <BriefingPanel detail={detail} mode={mode} />
      </div>

      {/* center: editor — min-w-0 lets the 1fr column shrink instead of Monaco's min-content
          width overflowing the grid and pushing the run panel off-screen. */}
      <div data-tour="editor" className="min-h-[55vh] min-w-0 overflow-hidden lg:min-h-0">
        {files.length > 0 ? (
          <EditorPanel files={editorFiles} onChange={onEdit} onReset={onReset} />
        ) : (
          <p className="p-4 text-sm text-muted">setting up your session…</p>
        )}
      </div>

      {/* right: run / trace + invariant board */}
      <div data-tour="run" className="flex min-h-[45vh] flex-col border-t border-border bg-panel lg:min-h-0 lg:border-t-0 lg:border-l">
        <div className="flex flex-col gap-2 border-b border-border p-3">
          <div className="flex items-center gap-2">
            <label htmlFor="task-select" className="sr-only">
              Test task
            </label>
            <select
              id="task-select"
              aria-label="Test task"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              className="min-w-0 flex-1 truncate rounded border border-border bg-panel-2 px-2 py-1 text-xs mono"
            >
              {tasks.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <div className="ml-auto flex shrink-0 items-center gap-1">
              <Tour tourKey="workspace" steps={WORKSPACE_TOUR} />
              <Button size="sm" data-tour="walkthrough" onClick={() => setHelpOpen(true)}>
                <HelpCircle size={14} /> Walkthrough
              </Button>
            </div>
          </div>
          <div data-tour="run-mode" className="hidden md:block">
            <RunModeBadge onLiveRun={runLive} busy={liveBusy} />
          </div>
        </div>

        <div data-tour="invariants" className="border-b border-border p-3">
          <InvariantBoard cells={invariantCells} />
        </div>

        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as "run" | "trace" | "timeline")}
          className="flex min-h-0 flex-1 flex-col"
        >
          <TabsList className="px-2">
            <TabsTrigger value="run">Run</TabsTrigger>
            <TabsTrigger value="trace" data-tour="trace-tab">Trace</TabsTrigger>
            <TabsTrigger value="timeline" data-tour="timeline-tab">Agent timeline</TabsTrigger>
          </TabsList>
          <div className="min-h-0 flex-1 overflow-auto p-3">
            <TabsContent value="run">
              <RunPanel onRun={onRun} running={running} result={result} logLines={logLines} />
            </TabsContent>
            <TabsContent value="trace">
              {trace ? (
                <TraceGraph trace={trace} />
              ) : (
                <p className="text-xs text-muted">Select the Trace tab to run and visualize.</p>
              )}
            </TabsContent>
            <TabsContent value="timeline">
              {trace ? (
                <>
                  {trace.dual_score && <DualScorePanel score={trace.dual_score} />}
                  <AgentTimeline trace={trace} />
                </>
              ) : (
                <p className="text-xs text-muted">Select the Agent timeline tab to run and visualize.</p>
              )}
            </TabsContent>
          </div>
        </Tabs>
      </div>
      </div>

      <HelpDrawer
        open={helpOpen}
        onOpenChange={setHelpOpen}
        challengeId={id}
        sessionId={sid}
        mode={mode}
      />

      {demo && demoOpen && sid && task && (
        <GuidedDemoRunner steps={demoSteps} onClose={() => setDemoOpen(false)} />
      )}
    </div>
  );
}
