"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Lightbulb, ListChecks, Eye, Bot, Send } from "lucide-react";
import { Drawer, Modal } from "./ui/dialog";
import { Button } from "./ui/button";
import { api } from "@/lib/api";
import type { HintsIndex, Hint, Walkthrough } from "@/lib/types";

export function HelpDrawer({
  open,
  onOpenChange,
  challengeId,
  sessionId,
  mode = "learn",
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  challengeId: string;
  sessionId: string | null;
  mode?: "learn" | "ctf";
}) {
  const locked = mode === "ctf";
  const [index, setIndex] = useState<HintsIndex | null>(null);
  const [hints, setHints] = useState<Hint[]>([]);
  const [walk, setWalk] = useState<Walkthrough | null>(null);
  const [confirmSolution, setConfirmSolution] = useState(false);
  const [diff, setDiff] = useState<string | null>(null);
  const [tutorLog, setTutorLog] = useState<{ role: string; text: string }[]>([]);
  const [tutorInput, setTutorInput] = useState("");
  // null = still checking; false = not enabled/ready; true = ready to chat.
  const [tutorReady, setTutorReady] = useState<boolean | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    api
      .getSettings()
      .then((s) => !cancelled && setTutorReady(Boolean(s.tutor.enabled && s.model.ready)))
      .catch(() => !cancelled && setTutorReady(false));
    return () => {
      cancelled = true;
    };
  }, [open]);

  async function loadIndex() {
    if (!index) setIndex(await api.hintsIndex(challengeId, sessionId ?? undefined));
  }
  async function revealNext() {
    await loadIndex();
    const next = hints.length;
    const hint = await api.hint(challengeId, next, sessionId ?? undefined);
    setHints((h) => [...h, hint]);
  }
  async function loadWalkthrough() {
    if (!walk) setWalk(await api.walkthrough(challengeId));
  }
  async function revealSolution() {
    const s = await api.solution(challengeId, sessionId ?? undefined);
    setDiff(s.diff);
    setConfirmSolution(false);
  }
  async function askTutor() {
    if (!sessionId || !tutorInput.trim()) return;
    const q = tutorInput.trim();
    setTutorInput("");
    setTutorLog((l) => [...l, { role: "you", text: q }]);
    try {
      const { reply } = await api.tutor(sessionId, q);
      setTutorLog((l) => [...l, { role: "tutor", text: reply }]);
    } catch {
      setTutorLog((l) => [...l, { role: "tutor", text: "(tutor error)" }]);
    }
  }

  const remaining = index ? index.count - hints.length : 1;

  return (
    <>
      <Drawer open={open} onOpenChange={onOpenChange} title="Walkthrough & Hints">
        <section className="mb-4">
          <h3 className="mb-1 flex items-center gap-1 text-xs uppercase text-muted">
            <Lightbulb size={13} /> Progressive hints
          </h3>
          <ol className="space-y-1 text-sm">
            {hints.map((h, i) => (
              <li key={i} className="rounded border border-border bg-panel-2 p-2">
                <span className="mono text-accent">{h.level}</span>
                <p className="text-muted">{h.text}</p>
              </li>
            ))}
          </ol>
          {locked ? (
            <p className="mt-2 text-xs text-muted">🔒 Hints are locked in CTF mode.</p>
          ) : (
            <Button size="sm" className="mt-2" onClick={revealNext} disabled={remaining <= 0}>
              {hints.length === 0 ? "Reveal first hint" : remaining > 0 ? "Reveal next hint" : "No more hints"}
            </Button>
          )}
        </section>

        <section className="mb-4">
          <h3 className="mb-1 flex items-center gap-1 text-xs uppercase text-muted">
            <ListChecks size={13} /> Guided walkthrough
          </h3>
          <p className="mb-2 rounded border border-border bg-panel-2 p-2 text-xs text-muted">
            You edit the <span className="mono text-accent">guardrails/vulnerable/…</span> file (the accent
            tab). The lock-badged tabs are read-only <span className="text-fg">environment</span>{" "}
            files — users, agents, resources, plans — describing the world the runtime runs
            against; you read them for context, you don&apos;t change them.
          </p>
          {walk ? (
            <ol className="list-decimal space-y-1 pl-4 text-sm text-muted">
              {walk.steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          ) : (
            <Button size="sm" onClick={loadWalkthrough}>
              Show walkthrough
            </Button>
          )}
        </section>

        <section className="mb-4">
          <h3 className="mb-1 flex items-center gap-1 text-xs uppercase text-muted">
            <Eye size={13} /> Solution
          </h3>
          {locked ? (
            <p className="text-xs text-muted">🔒 The solution is locked in CTF mode.</p>
          ) : diff ? (
            <pre className="max-h-56 overflow-auto rounded border border-border bg-panel-2 p-2 text-xs mono">
              {diff}
            </pre>
          ) : (
            <Button size="sm" variant="danger" onClick={() => setConfirmSolution(true)}>
              Reveal solution
            </Button>
          )}
        </section>

        <section>
          <h3 className="mb-1 flex items-center gap-1 text-xs uppercase text-muted">
            <Bot size={13} /> AI tutor
          </h3>
          {tutorReady === null ? (
            <p className="text-xs text-muted">Checking tutor availability…</p>
          ) : tutorReady === false ? (
            <p className="text-xs text-muted">
              The AI tutor isn&apos;t enabled on this server. Add a model provider key and
              enable it in{" "}
              <Link href="/settings" className="text-accent hover:underline">
                Settings
              </Link>{" "}
              to get adaptive coaching.
            </p>
          ) : (
            <>
              <div className="mb-2 max-h-40 space-y-1 overflow-auto text-sm">
                {tutorLog.map((m, i) => (
                  <div key={i}>
                    <span className="mono text-accent">{m.role}: </span>
                    <span className="text-muted">{m.text}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-1">
                <input
                  aria-label="Ask the AI tutor a question"
                  value={tutorInput}
                  onChange={(e) => setTutorInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && askTutor()}
                  placeholder={sessionId ? "Ask for a nudge…" : "start a session first"}
                  disabled={!sessionId}
                  className="flex-1 rounded border border-border bg-panel-2 px-2 py-1 text-sm outline-none focus:border-accent"
                />
                <Button size="sm" onClick={askTutor} disabled={!sessionId}>
                  <Send size={12} />
                </Button>
              </div>
            </>
          )}
        </section>
      </Drawer>

      <Modal
        open={confirmSolution}
        onOpenChange={setConfirmSolution}
        title="Reveal the full solution?"
      >
        <p className="mb-4 text-sm text-muted">
          This shows the reference fix as a diff. Try the tiered hints first — the learning is
          in deriving the control yourself.
        </p>
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="ghost" onClick={() => setConfirmSolution(false)}>
            Cancel
          </Button>
          <Button size="sm" variant="danger" onClick={revealSolution}>
            Reveal solution
          </Button>
        </div>
      </Modal>
    </>
  );
}
