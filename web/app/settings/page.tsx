"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, KeyRound, Server, Plug, Play } from "lucide-react";
import {
  api,
  ApiError,
  DEFAULT_API_BASE,
  getApiBase,
  setApiBase,
} from "@/lib/api";
import type { RunMode } from "@/lib/types";
import { Button } from "@/components/ui/button";

const INPUT =
  "w-full rounded border border-border bg-panel-2 px-2 py-1.5 text-sm outline-none focus:border-accent";

function Status({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={ok ? "inline-flex items-center gap-1 text-allow" : "inline-flex items-center gap-1 text-muted"}>
      {ok ? <CheckCircle2 size={13} /> : <XCircle size={13} />} {label}
    </span>
  );
}

export default function SettingsPage() {
  const { data: settings, refetch } = useQuery({
    queryKey: ["settings"],
    queryFn: api.getSettings,
  });

  // connection
  const [apiBase, setApiBaseInput] = useState("");
  const [conn, setConn] = useState<string | null>(null);
  useEffect(() => setApiBaseInput(getApiBase()), []);

  // model + run mode + tutor
  const [provider, setProvider] = useState("anthropic");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [runMode, setRunMode] = useState<RunMode>("deterministic");
  const [tutorEnabled, setTutorEnabled] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [testMsg, setTestMsg] = useState<string | null>(null);

  const keyReady = Boolean(settings?.model.ready);

  useEffect(() => {
    if (!settings) return;
    setProvider(settings.model.provider);
    setModel(settings.model.model ?? "");
    setRunMode(settings.run_mode);
    setTutorEnabled(settings.tutor.enabled);
  }, [settings]);

  async function saveConnection() {
    setApiBase(apiBase);
    await testConnection();
    refetch();
  }
  async function testConnection() {
    try {
      const { challenges } = await api.listChallenges();
      setConn(`✓ reachable — ${challenges.length} challenges`);
    } catch {
      setConn("✗ could not reach the API at this URL");
    }
  }

  async function saveSettings() {
    setSaved(null);
    await api.putSettings({
      provider,
      model,
      run_mode: runMode,
      tutor_enabled: tutorEnabled,
      ...(apiKey ? { api_key: apiKey } : {}),
    });
    setApiKey("");
    setSaved("Saved.");
    refetch();
  }
  async function testConn() {
    setTestMsg("testing…");
    try {
      const r = await api.testTutor();
      setTestMsg(r.ok ? `✓ model responded: ${r.reply || "ok"}` : `✗ ${r.error}`);
    } catch (e) {
      const m = e instanceof ApiError ? e.message : String(e);
      setTestMsg(`✗ ${m}`);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-lg font-semibold">Settings</h1>
      <p className="mt-1 text-sm text-muted">
        Configure what DVAH needs to run. API keys entered here are held in the server&apos;s
        memory only, never written to disk and never shown back in full. For production, prefer
        environment variables or a secrets manager.
      </p>

      {/* Connection */}
      <section className="mt-8 rounded border border-border bg-panel p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Plug size={15} className="text-accent" /> Connection
        </h2>
        <label htmlFor="api-base" className="mt-3 block text-xs uppercase tracking-wide text-muted">
          DVAH API base URL
        </label>
        <div className="mt-1 flex gap-2">
          <input
            id="api-base"
            className={INPUT}
            value={apiBase}
            placeholder={DEFAULT_API_BASE}
            onChange={(e) => setApiBaseInput(e.target.value)}
          />
          <Button size="sm" onClick={saveConnection}>
            Save &amp; test
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted">
          Stored in your browser (localStorage), overriding the build-time default. Clear it to
          fall back to <span className="mono">{DEFAULT_API_BASE}</span>.
        </p>
        {conn && <p className="mt-1 text-xs">{conn}</p>}
      </section>

      {/* Model & API (generic — powers tutor + live runs) */}
      <section className="mt-6 rounded border border-border bg-panel p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <KeyRound size={15} className="text-accent" /> Model &amp; API
        </h2>
        <p className="mt-1 text-xs text-muted">
          One model provider + key, used for <strong>both</strong> the optional AI tutor and{" "}
          <strong>live agent runs</strong>. Anthropic/OpenAI take an API key; Bedrock accepts a
          Bedrock API key, or leave it blank to use the server&apos;s AWS credentials (access
          key / profile / role). Solving labs (the deterministic runs) never needs a key.
        </p>

        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="provider" className="block text-xs uppercase tracking-wide text-muted">Provider</label>
            <select id="provider" className={INPUT} value={provider} onChange={(e) => setProvider(e.target.value)}>
              {(settings?.providers ?? ["anthropic", "openai", "bedrock"]).map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="model" className="block text-xs uppercase tracking-wide text-muted">
              Model (optional)
            </label>
            <input
              id="model"
              className={INPUT}
              value={model}
              placeholder="provider default"
              onChange={(e) => setModel(e.target.value)}
            />
          </div>
          <div className="sm:col-span-2">
            <label htmlFor="api-key" className="block text-xs uppercase tracking-wide text-muted">
              {provider === "bedrock" ? "Bedrock API key (optional)" : "API key"}
            </label>
            <input
              id="api-key"
              className={INPUT}
              type="password"
              value={apiKey}
              placeholder={
                settings?.model.key_set
                  ? `set (${settings.model.key_hint}, via ${settings.model.key_source})`
                  : provider === "bedrock"
                    ? "paste a Bedrock API key, or leave blank for AWS creds"
                    : "paste key — stored in server memory only"
              }
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button size="sm" onClick={saveSettings}>
            Save settings
          </Button>
          <Button size="sm" variant="ghost" onClick={testConn}>
            Test connection
          </Button>
          {settings && (
            <Status ok={keyReady} label={keyReady ? "credentials ready" : "no key configured"} />
          )}
          {saved && <span className="text-xs text-allow">{saved}</span>}
        </div>
        {testMsg && <p className="mt-2 text-xs text-muted">{testMsg}</p>}
      </section>

      {/* Run mode (single global choice) */}
      <section className="mt-6 rounded border border-border bg-panel p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Play size={15} className="text-accent" /> Run mode
        </h2>
        <p className="mt-1 text-xs text-muted">
          How lab agent runs execute — one setting for every lab.{" "}
          <strong>Deterministic</strong> (default) is the reproducible, key-free security oracle
          that grades every lab. <strong>Live</strong> runs the agent through your real model
          (billable) and shows the agent timeline + the two scores. Replay is a CLI-only path
          (<span className="mono">dvah replay &lt;recording&gt;</span>).
        </p>
        <div className="mt-3 flex flex-wrap gap-2" role="radiogroup" aria-label="Run mode">
          {(["deterministic", "live"] as RunMode[]).map((m) => {
            const disabled = m === "live" && !keyReady;
            const active = runMode === m;
            return (
              <button
                key={m}
                type="button"
                role="radio"
                aria-checked={active}
                data-run-mode={m}
                disabled={disabled}
                title={disabled ? "Configure a model key above to enable live runs." : undefined}
                onClick={() => setRunMode(m)}
                className={
                  active
                    ? "rounded border border-accent/60 bg-accent/10 px-3 py-1 text-sm text-accent"
                    : "rounded border border-border px-3 py-1 text-sm text-muted hover:border-accent disabled:cursor-not-allowed disabled:opacity-50"
                }
              >
                {m === "live" ? "Live (real model)" : "Deterministic (default)"}
                {disabled && " · set a key"}
              </button>
            );
          })}
          <Button size="sm" onClick={saveSettings}>
            Save
          </Button>
        </div>
      </section>

      {/* AI tutor (optional feature sharing the model above) */}
      <section className="mt-6 rounded border border-border bg-panel p-4">
        <h2 className="text-sm font-semibold">AI tutor</h2>
        <p className="mt-1 text-xs text-muted">
          Optional Socratic hint chat in the lab workspace. It shares the Model &amp; API above —
          no separate key.
        </p>
        <div className="mt-3 flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={tutorEnabled}
              onChange={(e) => setTutorEnabled(e.target.checked)}
            />
            Enable AI tutor hints
          </label>
          <Button size="sm" onClick={saveSettings}>
            Save
          </Button>
        </div>
      </section>

      {/* Server config (read-only) */}
      <section className="mt-6 rounded border border-border bg-panel p-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Server size={15} className="text-accent" /> Server configuration
        </h2>
        <p className="mt-1 text-xs text-muted">
          Set via environment variables on the API container (read-only here).
        </p>
        {settings && (
          <dl className="mt-3 grid grid-cols-[160px_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted">Runner</dt>
            <dd className="mono">{settings.server.runner}</dd>
            <dt className="text-muted">Run concurrency</dt>
            <dd className="mono">{settings.server.run_concurrency}</dd>
            <dt className="text-muted">CORS origins</dt>
            <dd className="mono">{settings.server.cors_origins}</dd>
            <dt className="text-muted">Provider keys in env</dt>
            <dd className="flex flex-wrap gap-3">
              {Object.entries(settings.env_keys).map(([p, present]) => (
                <Status key={p} ok={present} label={p} />
              ))}
            </dd>
          </dl>
        )}
      </section>
    </div>
  );
}
