"use client";
import { Term } from "./term";
import type { ChallengeDetail } from "@/lib/types";

// One scrollable briefing (no tabs): what you're fixing → the rule at stake → how
// authority flows → environment → read-only runtime source. CTF mode hides the
// invariant/boundary sections (they'd give the game away).
export function BriefingPanel({
  detail,
  mode,
}: {
  detail: ChallengeDetail;
  mode: "learn" | "ctf";
}) {
  const learn = mode === "learn";
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-3 py-2">
        <div className="mono text-accent">{detail.id}</div>
        <div className="text-sm font-semibold">{detail.title}</div>
        <div className="text-xs text-muted">
          difficulty: {detail.difficulty}
          {detail.estimated_minutes ? ` · ~${detail.estimated_minutes} min` : ""}
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-auto p-3 text-sm">
        {/* What you're fixing */}
        <section>
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted">What you&apos;re fixing</h2>
          <p>{detail.objective_exploit}</p>
          {learn && detail.objective_fix && (
            <p className="mt-2 text-muted">
              <span className="text-fg">Fix goal: </span>
              {detail.objective_fix}
            </p>
          )}
          <p className="mt-2 text-xs text-muted">
            Files to patch:{" "}
            {detail.editable_files.map((f) => (
              <span key={f.path} className="mono text-accent">
                {f.path}{" "}
              </span>
            ))}
          </p>
          {learn && (
            <p className="mt-3 rounded border border-border bg-panel-2 p-2 text-xs text-muted">
              Stuck? Open <span className="text-accent">Walkthrough</span> (top-right of the
              run panel) for tiered hints, a step-by-step guide, and — as a last resort —
              the full solution.
            </p>
          )}
        </section>

        {learn && detail.invariants.length > 0 && (
          <section>
            <h2 className="mb-1 text-xs uppercase tracking-wide text-muted">
              The rule at stake — the <Term id="invariant">invariant</Term>
            </h2>
            <ul className="space-y-2">
              {detail.invariants.map((i) => (
                <li key={i.id}>
                  <span className="mono text-accent">{i.id}</span>
                  <p className="text-muted">{i.statement}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {learn && (
          <section>
            <h2 className="mb-1 text-xs uppercase tracking-wide text-muted">How authority flows</h2>
            <p className="text-muted">
              The <Term id="harness">harness</Term> is what confers authority. This lab
              breaks a control in{" "}
              <span className="mono text-fg">{detail.overridden_slots.join(", ") || "the harness"}</span>
              {detail.components.length > 0 && <> (components: {detail.components.join(", ")})</>}. Authority
              flows through the <Term id="action-envelope">ActionEnvelope</Term> gate — the
              plan proposes, the envelope carries authority.
            </p>
          </section>
        )}

        {/* All read-only context now opens as grouped tabs in the editor — the environment
            (world) and the harness modules the code calls into (reference). */}
        <section>
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted">Read-only context</h2>
          <p className="text-xs text-muted">
            Everything you read (but don&apos;t edit) is open as{" "}
            <span className="text-fg">read-only tabs in the editor →</span>, lock-badged and
            grouped: <span className="text-fg">the world</span> the runtime runs against (users,
            agents, resources, plans){detail.references?.length > 0 && (
              <>
                {" "}
                and <span className="text-fg">the harness reference</span> — the modules your code
                calls into (under &ldquo;Reference files&rdquo;)
              </>
            )}
            . You patch the accent tab.
          </p>
        </section>
      </div>
    </div>
  );
}
