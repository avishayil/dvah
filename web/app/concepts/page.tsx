import Link from "next/link";
import { GLOSSARY } from "@/lib/glossary";

export const metadata = {
  title: "Learn — DVAH",
  description: "The vocabulary behind DVAH, each term with a concrete example and a lab.",
};

// Ordered so it reads as a short narrative, not an A–Z dump.
const ORDER = [
  "harness",
  "agent-runtime",
  "model-session",
  "action",
  "action-envelope",
  "authorization",
  "capability",
  "tool",
  "tool-definition",
  "skill",
  "delegation",
  "approval",
  "provenance",
  "secret-broker",
  "mcp",
  "invariant",
  "exploit-patch-prove",
  "toctou",
];

export default function ConceptsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold">Learn the concepts</h1>
      <p className="mt-2 text-sm text-muted">
        DVAH is for engineers building AI agents — you don&apos;t need a security
        background. Each term below comes with a concrete example and a link to the lab
        that teaches it hands-on.
      </p>

      {/* Entry-level framing: what the whole project is about, before the vocabulary. */}
      <section className="mt-6 rounded border border-accent/40 bg-accent/5 p-4">
        <h2 className="text-base font-semibold text-fg">What is an agent harness?</h2>
        <p className="mt-2 text-sm text-muted">
          When you give an LLM tools — let it read files, call APIs, spend money, touch
          prod — something has to sit between the model and the real world and decide, for
          every single action, &ldquo;is this allowed, right now?&rdquo; That something is
          the <span className="text-fg">harness</span>. The model only <em>proposes</em> what
          to do; the harness is what actually <em>confers authority</em> and runs it — after
          checking authorization, human approval, capabilities, data provenance, and
          secrets.
        </p>
        <p className="mt-2 text-sm text-muted">
          Why it matters: models can be tricked (a poisoned issue, a confusing prompt). You
          can&apos;t make a model un-trickable — but if the <span className="text-fg">harness</span>{" "}
          is correct, the dangerous action is blocked no matter what talked the model into
          proposing it. DVAH is a deliberately-insecure harness: you exploit a real bug in
          it, see why, patch the runtime, and prove the fix holds. Best first step —{" "}
          <Link
            href="/labs/DVAH-001-plan-time-authorization?mode=learn&demo=1"
            className="text-accent underline"
          >
            watch the guided DVAH-001 demo →
          </Link>
        </p>
      </section>

      <div className="mt-8 space-y-5">
        {ORDER.map((id) => {
          const e = GLOSSARY[id];
          if (!e) return null;
          return (
            <section key={id} className="rounded border border-border bg-panel p-4">
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="text-base font-semibold text-fg">{e.term}</h2>
                {e.lab && (
                  <Link
                    href={`/labs/${e.lab}?mode=learn`}
                    className="mono text-xs text-accent hover:underline"
                  >
                    learn in {e.lab} →
                  </Link>
                )}
              </div>
              <p className="mt-1 text-sm text-accent">{e.short}</p>
              <p className="mt-2 text-sm text-muted">{e.long}</p>
              <div className="mt-3 rounded border border-border bg-panel-2 p-2.5">
                <span className="mono text-[10px] uppercase tracking-wide text-muted">
                  Example
                </span>
                <p className="mt-1 text-sm text-fg">{e.example}</p>
              </div>
            </section>
          );
        })}
      </div>

      {/* Practice section — Chaos mode + conformance live under Learn, not the top nav. */}
      <h2 className="mt-10 text-lg font-semibold">Practice &amp; assessment</h2>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <section className="rounded border border-border bg-panel p-4">
          <h3 className="text-base font-semibold text-fg">{GLOSSARY.mutation.term}</h3>
          <p className="mt-1 text-sm text-accent">{GLOSSARY.mutation.short}</p>
          <p className="mt-2 text-sm text-muted">{GLOSSARY.mutation.long}</p>
          <div className="mt-3 rounded border border-border bg-panel-2 p-2.5">
            <span className="mono text-[10px] uppercase tracking-wide text-muted">Example</span>
            <p className="mt-1 text-sm text-fg">{GLOSSARY.mutation.example}</p>
          </div>
          <Link
            href="/mutate"
            className="mt-3 inline-block text-sm text-accent hover:underline"
          >
            Open Chaos mode →
          </Link>
        </section>
        <section className="rounded border border-border bg-panel p-4">
          <h3 className="text-base font-semibold text-fg">{GLOSSARY.conformance.term}</h3>
          <p className="mt-1 text-sm text-accent">{GLOSSARY.conformance.short}</p>
          <p className="mt-2 text-sm text-muted">{GLOSSARY.conformance.long}</p>
          <div className="mt-3 rounded border border-border bg-panel-2 p-2.5">
            <span className="mono text-[10px] uppercase tracking-wide text-muted">Example</span>
            <p className="mt-1 text-sm text-fg">{GLOSSARY.conformance.example}</p>
          </div>
          <p className="mt-3 text-xs text-muted">Run it from the CLI: <span className="mono">dvah conformance</span></p>
        </section>
      </div>

      <p className="mt-10 text-sm text-muted">
        Ready to try it?{" "}
        <Link href="/labs/DVAH-001-plan-time-authorization?mode=learn&demo=1" className="text-accent underline">
          Watch the guided DVAH-001 demo →
        </Link>
      </p>
    </div>
  );
}
