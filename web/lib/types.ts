// A file shown in the editor. `writable:false` = read-only reference tab. `group` drives
// the labeled tab clusters (the editable file you patch, the read-only world, the read-only
// harness reference); `label` is the tab's display name (defaults to `path`).
export type EditableFileGroup = "patch" | "world" | "reference";
export type EditableFile = {
  path: string;
  contents: string;
  writable?: boolean;
  group?: EditableFileGroup;
  label?: string;
};

export type LabMeta = {
  order: number;
  estimated_minutes: number | null;
  teaches: string | null;
  prerequisites: string[];
};

export type ChallengeSummary = {
  id: string;
  title: string;
  difficulty: string;
  invariants: string[];
  objective: string;
  blurb: string;
} & LabMeta;

export type InvariantRef = { id: string; statement: string };

export type RefModule = { module: string; contents: string };

// File-based artifacts declared by a lab: loadable skills (SKILL.md), agent definitions
// (agents/*.md), and the built-in tool catalog. Compact, values-only — no secrets.
export type Artifacts = {
  skills: {
    role: string;
    name: string;
    version: string;
    description: string;
    requested_permissions: string[];
    tools: string[];
  }[];
  agents: {
    agent_id: string;
    description: string;
    model: string;
    tools: string[];
    skills: string[];
  }[];
  tools: { id: string; name: string; description: string }[];
};

export type ChallengeDetail = {
  id: string;
  title: string;
  difficulty: string;
  invariants: InvariantRef[];
  objective_exploit: string;
  objective_fix: string;
  readme_markdown: string;
  environment: { users: unknown; agents: unknown; resources_summary: unknown };
  editable_files: EditableFile[];
  references: RefModule[];
  artifacts: Artifacts;
  tasks: string[];
  overridden_slots: string[];
  components: string[];
} & LabMeta;

export type Session = {
  session_id: string;
  editable_files: EditableFile[];
  readonly_files?: EditableFile[];
  tasks: string[];
};

export type TestOutcome = "passed" | "failed" | "error";
export type TestResult = {
  name: string;
  marker: string;
  outcome: TestOutcome;
  message?: string;
};

export type InvariantStatus = {
  holding: number;
  total: number;
  per: { id: string; holds: boolean }[];
};

export type RunResult = {
  tests: TestResult[];
  invariants: InvariantStatus;
  stdout: string;
  exit_code: number;
};

export type TraceEvent = {
  kind: string;
  task_id: string;
  action_hash: string | null;
  detail: Record<string, unknown>;
};

export type TraceSummary = {
  total_events: number;
  executed: number;
  denials: { action_hash: string | null; invariant: string | null }[];
  unauthorized_executions: string[];
  delegations: string[];
  untrusted_instruction: boolean;
};

export type RuntimeSecurity = {
  secure: boolean;
  unauthorized: string[];
  basis: string;
};

export type LiveAgentExercise = {
  attempted: boolean;
  blocked: boolean;
  recovered: boolean;
  avoided: boolean;
  proposed_ops: string[];
  summary: string;
};

export type DualScore = {
  runtime_security: RuntimeSecurity;
  live_agent_exercise: LiveAgentExercise;
};

export type LiveExperience = {
  attack_likelihood?: string;
  expected_paths?: string[];
} | null;

export type TraceResult = {
  events: TraceEvent[];
  summary: TraceSummary;
  halted?: { error: string };
  // Additive (v0.3 Phase 7a): the two independent scores + optional live-run metadata.
  dual_score?: DualScore;
  live_experience?: LiveExperience;
};

export type HintsIndex = {
  invariant: string;
  count: number;
  tiers: { level: string; revealed: boolean }[];
};
export type Hint = { level: string; text: string };
export type Walkthrough = { steps: string[] };
export type SolutionReveal = { files: EditableFile[]; diff: string };
export type MutateResult = {
  holding: number;
  total: number;
  per: { id: string; holds: boolean }[];
  revealed?: string[];
};

export type RunMode = "deterministic" | "live";

export type SettingsView = {
  providers: string[];
  run_modes: RunMode[];
  run_mode: RunMode;
  // Generic model credentials — shared by the AI tutor and live agent runs.
  model: {
    ready: boolean;
    provider: string;
    model: string | null;
    key_set: boolean;
    key_hint: string | null;
    key_source: "ui" | "env" | null;
  };
  tutor: { enabled: boolean };
  env_keys: Record<string, boolean>;
  server: { runner: string; run_concurrency: string; cors_origins: string };
};

export type SettingsUpdate = {
  tutor_enabled?: boolean;
  provider?: string;
  model?: string;
  api_key?: string;
  run_mode?: RunMode;
};

export type SessionProgress = {
  mode: "learn" | "ctf";
  runs: number;
  hints_revealed: number;
  time_to_first_all_green_s: number | null;
  events: Record<string, unknown>[];
};
