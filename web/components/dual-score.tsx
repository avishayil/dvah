import { cn } from "./ui/utils";
import type { DualScore } from "@/lib/types";
import { ShieldCheck, ShieldAlert, Bot } from "lucide-react";

/**
 * The two independent scores DVAH teaches to keep separate:
 *  - Runtime Security — model-independent: could a dangerous action execute if proposed?
 *  - Live Agent Exercise — what THIS run's model actually did.
 * A model avoiding the bait does NOT make the architecture secure — surfaced explicitly
 * when the exercise "avoided" but the runtime is still insecure.
 */
export function DualScorePanel({ score }: { score: DualScore }) {
  const sec = score.runtime_security;
  const ex = score.live_agent_exercise;
  const avoidedButVulnerable = ex.avoided && !sec.secure;

  return (
    <div data-testid="dual-score" className="mb-3 grid gap-2 sm:grid-cols-2">
      {/* Runtime Security — the authoritative, deterministic verdict. */}
      <div
        data-testid="runtime-security"
        data-secure={sec.secure ? "true" : "false"}
        className={cn(
          "rounded-lg border p-3",
          sec.secure ? "border-allow/50 bg-allow/5" : "border-deny/50 bg-deny/5",
        )}
      >
        <div className="flex items-center gap-1.5 text-sm font-medium">
          {sec.secure ? (
            <ShieldCheck size={15} className="text-allow" />
          ) : (
            <ShieldAlert size={15} className="text-deny" />
          )}
          Runtime Security
        </div>
        <div className={cn("mt-1 text-sm", sec.secure ? "text-allow" : "text-deny")}>
          {sec.secure
            ? "Harness held — every executed action was authorized."
            : `Vulnerable — ${sec.unauthorized.length} action(s) executed without authorization.`}
        </div>
        <div className="mt-1 text-[11px] text-muted">
          Objective &amp; model-independent · {sec.basis}
        </div>
      </div>

      {/* Live Agent Exercise — what the model did this run. */}
      <div data-testid="agent-exercise" className="rounded-lg border border-border bg-panel p-3">
        <div className="flex items-center gap-1.5 text-sm font-medium">
          <Bot size={15} className="text-accent" /> Live Agent Exercise
        </div>
        <div className="mt-1 text-sm text-fg">{ex.summary}</div>
        <div className="mt-1 flex flex-wrap gap-1 text-[11px]">
          {ex.attempted && <span className="rounded-full bg-warn/15 px-1.5 text-warn">attempted</span>}
          {ex.blocked && <span className="rounded-full bg-deny/15 px-1.5 text-deny">blocked</span>}
          {ex.recovered && <span className="rounded-full bg-info/15 px-1.5 text-info">recovered</span>}
          {ex.avoided && <span className="rounded-full bg-allow/15 px-1.5 text-allow">avoided</span>}
        </div>
      </div>

      {avoidedButVulnerable && (
        <div
          data-testid="avoided-warning"
          className="rounded-lg border border-warn/50 bg-warn/5 p-3 text-xs text-warn sm:col-span-2"
        >
          The model avoided the bait — but that does <strong>not</strong> mean the architecture
          is secure. Runtime Security (the deterministic verifier, above) still reports the
          harness is vulnerable: a different model, or the same model tomorrow, could take it.
        </div>
      )}
    </div>
  );
}
