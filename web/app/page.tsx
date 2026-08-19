"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Bug,
  CheckCircle2,
  GitBranch,
  Radar,
  ScrollText,
  ShieldCheck,
  Wrench,
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Term } from "@/components/term";

// The loop condensed to the four things YOU actually do, in order.
const HOW = [
  { label: "Exploit", icon: Bug, you: "run the attack and watch it succeed" },
  { label: "Trace", icon: GitBranch, you: "see step-by-step why it worked" },
  { label: "Patch", icon: Wrench, you: "edit a few lines in the runtime" },
  { label: "Prove", icon: CheckCircle2, you: "tests + hidden mutations go green" },
] as const;

// What makes DVAH different from a tutorial — the three load-bearing ideas.
const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Invariant-first grading",
    body: "You aren't graded on style. Each lab pins a security rule an agent runtime must never break, and your fix has to make that rule hold.",
  },
  {
    icon: Radar,
    title: "Adversarial by design",
    body: "A chaos engine mutates the attack after you patch. A fix that only handles the demo won't survive the unseen variations.",
  },
  {
    icon: ScrollText,
    title: "Live trace + two scores",
    body: "Watch the agent loop lane by lane — model → policy → tool. Run deterministically, against a live model, or replay a recording, and read two scores: the deterministic runtime-security verdict and what the model actually did.",
  },
] as const;

// Each invariant with a one-line summary + the lab that teaches it.
const RULES: { id: string; plain: string; lab: string }[] = [
  { id: "INV-01", plain: "Check permission for every action right before it runs.", lab: "DVAH-001" },
  { id: "INV-02", plain: "A sub-agent can't be more powerful than its parent.", lab: "DVAH-002" },
  { id: "INV-03", plain: "Human approval is tied to the exact action, not the plan.", lab: "DVAH-007" },
  { id: "INV-04", plain: "Secrets never reach the model's context.", lab: "DVAH-004" },
  { id: "INV-05", plain: "Every value keeps a 'where did this come from?' tag.", lab: "DVAH-005" },
  { id: "INV-06", plain: "Untrusted data can't become instructions; delegation can't mint budget.", lab: "DVAH-003" },
  { id: "INV-07", plain: "A skill update can't silently gain new powers.", lab: "DVAH-009" },
  { id: "INV-08", plain: "Every action is attributable to a person + agent + delegation chain.", lab: "DVAH-008" },
  { id: "INV-09", plain: "Authority is re-checked before every action; revocation takes effect.", lab: "DVAH-010" },
  { id: "INV-10", plain: "Memory stays per-tenant and never acts as an instruction.", lab: "DVAH-011" },
  { id: "INV-11", plain: "Approval is tied to the tool's identity/version.", lab: "DVAH-012" },
  { id: "INV-12", plain: "Security checks are atomic — races can't sneak past a limit.", lab: "DVAH-013" },
  { id: "INV-13", plain: "Authorization checks the exact operation, not just the tool.", lab: "DVAH-008" },
  { id: "INV-14", plain: "Runtime boundaries are contained — the harness limits egress and pins tool-server identity.", lab: "DVAH-014" },
];

const AUDIENCE = [
  { role: "Backend engineers", why: "shipping tool-calling agents into real services" },
  { role: "Platform engineers", why: "owning the runtime other teams build agents on" },
  { role: "AppSec engineers", why: "who need agent threats in the muscle, not the slides" },
] as const;

const DIFF_COLOR: Record<string, string> = {
  easy: "border-allow/50 text-allow",
  medium: "border-warn/50 text-warn",
  hard: "border-deny/50 text-deny",
};

export default function LandingPage() {
  const { data } = useQuery({ queryKey: ["challenges"], queryFn: api.listChallenges });
  const labs = data?.challenges ?? [];
  const labCount = labs.length || 14;

  return (
    <div className="mx-auto max-w-6xl px-6">
      {/* hero */}
      <section className="hero-glow reveal py-16 text-center sm:py-20">
        <div className="mono text-xs uppercase tracking-widest text-accent">
          Damn Vulnerable Agent Harness
        </div>
        <h1 className="mx-auto mt-4 max-w-4xl text-balance text-4xl font-semibold leading-[1.1] sm:text-5xl">
          Make your AI agents safe — by <span className="text-accent">breaking one</span> and
          fixing it.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted">
          DVAH is a hands-on lab for engineers who ship agents that call tools, spend money,
          or touch prod. Take a deliberately-insecure{" "}
          <Term id="agent-runtime">agent runtime</Term>, exploit a real architectural bug,
          see exactly why it happened, patch it, and prove the fix holds —{" "}
          <span className="text-fg">no security background needed.</span>
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link href="/demo">
            <Button variant="primary" className="h-11 px-6 text-base">
              Start with DVAH-001 <ArrowRight size={16} />
            </Button>
          </Link>
          <Link href="/concepts">
            <Button variant="default" className="h-11 px-6 text-base">
              Learn the concepts
            </Button>
          </Link>
          <span className="text-xs text-muted">a guided walkthrough · ~2 min · no setup</span>
        </div>
      </section>

      {/* stat strip */}
      <section aria-label="At a glance" className="reveal flex flex-wrap justify-center gap-3 pb-4">
        <span className="pill text-sm">
          <span className="font-semibold text-fg">{labCount}</span>
          <span className="text-muted">labs</span>
        </span>
        <span className="pill text-sm">
          <span className="font-semibold text-fg">14</span>
          <span className="text-muted">invariants</span>
        </span>
        <span className="pill text-sm text-muted">
          exploit <span className="text-accent">→</span> patch{" "}
          <span className="text-accent">→</span> prove
        </span>
        <span className="pill text-sm">
          <span className="font-semibold text-fg">4</span>
          <span className="text-muted">test tiers per lab</span>
        </span>
      </section>

      {/* how it works */}
      <section className="reveal py-14">
        <h2 className="text-center text-2xl font-semibold">How a lab works</h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-sm text-muted">
          Every lab is the same loop. It takes about ten minutes and you steer the whole way.
        </p>
        <ol className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW.map((s, i) => (
            <li key={s.label} className="soft-card p-5">
              <div className="flex items-center gap-2">
                <s.icon size={18} className="shrink-0 text-accent" />
                <span className="mono text-xs text-muted">Step {i + 1}</span>
              </div>
              <div className="mt-3 text-lg font-medium">{s.label}</div>
              <div className="mt-1 text-sm text-muted">{s.you}</div>
            </li>
          ))}
        </ol>
      </section>

      {/* features */}
      <section className="reveal py-14">
        <h2 className="text-center text-2xl font-semibold">Not a tutorial — a harness</h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-sm text-muted">
          The runtime is real, the bugs are architectural, and your fix has to earn it.
        </p>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="soft-card p-6">
              <f.icon size={22} className="text-accent" />
              <h3 className="mt-4 text-base font-medium">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* who it's for */}
      <section className="reveal py-14">
        <div className="grad-band rounded-2xl px-6 py-8 sm:px-10">
          <h2 className="text-center text-2xl font-semibold">Who it&apos;s for</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {AUDIENCE.map((a) => (
              <div key={a.role} className="text-center">
                <div className="text-sm font-medium text-fg">{a.role}</div>
                <div className="mt-1 text-sm text-muted">{a.why}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* invariants */}
      <section className="reveal py-14">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-2xl font-semibold">The 14 rules a safe runtime never breaks</h2>
          <Link href="/concepts" className="text-sm text-accent hover:underline">
            what&apos;s an <Term id="invariant">invariant</Term>? →
          </Link>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          {RULES.map((r) => (
            <Link
              key={r.id}
              href={`/labs/${r.lab}?mode=learn`}
              className="soft-card group flex items-start gap-3 p-4"
            >
              <span className="mono text-xs text-accent">{r.id}</span>
              <span className="min-w-0 flex-1 text-sm text-muted group-hover:text-fg">
                {r.plain}
              </span>
            </Link>
          ))}
        </div>
      </section>

      {/* labs preview */}
      <section className="reveal py-14">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-2xl font-semibold">{labCount} labs · beginner → advanced</h2>
          <Link href="/labs" className="text-sm text-accent hover:underline">
            open all →
          </Link>
        </div>
        {labs.length > 0 ? (
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            {labs.map((c) => (
              <Link
                key={c.id}
                href={`/labs/${c.id}?mode=learn`}
                className="soft-card group p-4"
              >
                <div className="flex items-center gap-2">
                  <span className="mono text-xs text-accent">{c.id}</span>
                  <span className="min-w-0 flex-1 truncate text-sm group-hover:text-fg">
                    {c.title}
                  </span>
                  <span
                    className={`rounded-full border px-2 py-0.5 text-[10px] ${DIFF_COLOR[c.difficulty] ?? "border-border text-muted"}`}
                  >
                    {c.difficulty || "?"}
                  </span>
                </div>
                {c.teaches && (
                  <div className="mt-1.5 text-xs text-muted">
                    Learn: {c.teaches}
                    {c.estimated_minutes ? ` · ~${c.estimated_minutes} min` : ""}
                  </div>
                )}
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-6 text-sm text-muted">
            <Link href="/labs" className="text-accent hover:underline">
              Browse the labs →
            </Link>{" "}
            (start the DVAH API to see the live catalog)
          </p>
        )}
      </section>

      {/* closing CTA band */}
      <section className="reveal pb-20 pt-6">
        <div className="grad-band flex flex-col items-center gap-5 rounded-2xl px-6 py-12 text-center sm:px-10">
          <h2 className="max-w-2xl text-2xl font-semibold sm:text-3xl">
            Ready? Break your first agent runtime.
          </h2>
          <p className="max-w-xl text-sm text-muted">
            Start with the plan-time authorization bug in DVAH-001 — exploit it, trace it,
            and prove your patch holds.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link href="/demo">
              <Button variant="primary" className="h-11 px-6 text-base">
                Start with DVAH-001 <ArrowRight size={16} />
              </Button>
            </Link>
            <Link href="/labs">
              <Button variant="default" className="h-11 px-6 text-base">
                Browse all labs
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
