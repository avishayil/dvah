"use client";
import { Term } from "./term";
import type { Artifacts, ChallengeDetail } from "@/lib/types";

// Compact, read-only view of a lab's file-based artifacts: loadable skills (SKILL.md),
// agent definitions (agents/*.md), and the built-in tool catalog. Gated behind
// skills/agents presence — every lab has a tool catalog, so showing it unconditionally
// would clutter labs that declare no skills or agents. When shown, tools are listed too.
function ArtifactsSection({ artifacts }: { artifacts?: Artifacts }) {
  if (!artifacts) return null;
  const { skills, agents, tools } = artifacts;
  if (skills.length === 0 && agents.length === 0) return null;
  return (
    <section data-testid="artifacts-section">
      <h2 className="mb-1 text-xs uppercase tracking-wide text-muted">Artifacts</h2>
      {skills.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-fg">
            <Term id="skill">Skills</Term>
          </div>
          <ul className="mt-1 space-y-1">
            {skills.map((s) => (
              <li key={s.role} className="text-xs text-muted">
                <span className="mono text-accent">
                  {s.name}@{s.version}
                </span>{" "}
                ({s.role})
                {s.requested_permissions.length > 0 && (
                  <>
                    {" · requests "}
                    <span className="mono">{s.requested_permissions.join(", ")}</span>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {agents.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-fg">Agents</div>
          <ul className="mt-1 space-y-1">
            {agents.map((a) => (
              <li key={a.agent_id} className="text-xs text-muted">
                <span className="mono text-accent">{a.agent_id}</span>
                {a.tools.length > 0 && (
                  <>
                    {" · tools "}
                    <span className="mono">{a.tools.join(", ")}</span>
                  </>
                )}
                {a.skills.length > 0 && (
                  <>
                    {" · skills "}
                    <span className="mono">{a.skills.join(", ")}</span>
                  </>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {tools.length > 0 && (
        <div>
          <div className="text-xs text-fg">
            <Term id="tool-definition">Tool catalog</Term>
          </div>
          <ul className="mt-1 space-y-1">
            {tools.map((t) => (
              <li key={t.id} className="text-xs text-muted">
                <span className="mono text-accent">{t.id}</span>
                {t.description && ` — ${t.description}`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

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

        <ArtifactsSection artifacts={detail.artifacts} />

        {/* All read-only context now opens as grouped tabs in the editor — the environment
            (world) and the harness modules the code calls into (reference). */}
        <section>
          <h2 className="mb-1 text-xs uppercase tracking-wide text-muted">Read-only context</h2>
          <p className="text-xs text-muted">
            Everything you read (but don&apos;t edit) is open as{" "}
            <span className="text-fg">read-only tabs in the editor →</span>, lock-badged and
            grouped: <span className="text-fg">the world</span> the runtime runs against (users,
            agents, resources, plans, plus any skills/SKILL.md and agent definitions){detail.references?.length > 0 && (
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
