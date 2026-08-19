# DVAH Architecture

```
User → Planner(Model) → Plan(proposal, NO authority)
                              │  resolve each step at execution time
                              ▼
                        ActionEnvelope (frozen, canonical)
                              │
      ┌───────────────── ActionBroker gate ─────────────────┐
      │ 1 resolve   2 construct   3 authorize (policy)       │
      │ 4 approve-if-required (binds to action_hash)         │
      │ 5 inject secrets (tool layer)  6 execute  7 provenance│
      └──────────────────────────────────────────────────────┘
                              ▼
                        ToolProvider  ──►  simulated services
                     (Native in-proc | HTTP FastAPI)
```

## Layout

- `dvah/models/` — pure frozen data (`ActionEnvelope` and its parts). No behavior.
- `dvah/security/` — first-class, swappable security services. Each is a `Protocol`
  plus a correct default (`Builtin*`). Challenges override these with broken versions.
- `dvah/harness/` — runtime plumbing: `resolver`, `broker` (the gate), `agent`
  (delegation), swappable `executor`, `Harness` driver, `RunContext`.
- `dvah/providers/` — the model seam (`ModelProvider.complete` one-shot, plus the
  stateful `ModelSession.next → ModelTurn`; `DeterministicModel`/`ContextActionModel`
  wrapped by `ScriptedSession`) and `ToolProvider` (`NativeToolProvider`,
  `HttpToolProvider`, `MCPToolProvider`, and `ToolRouter` to multiplex them).
- `dvah/services/` + top-level `services/` — in-memory stores and their FastAPI
  front-ends (identical behavior across transports; parity tested).
- `dvah/scenarios/loader.py` — turns a `scenario.yaml` into a runnable `Harness` by
  swapping named slots with the challenge's `vulnerable/` or `solution/` code.
- `challenges/DVAH-00N-*/` — labs. `vulnerable/` is shipped; `solution/` is the hidden
  reference; `tests/` holds functional/exploit/invariant(/adversarial) suites.

## Why harness/ and security/ are split

Many labs are "the developer put the security check in the wrong place." Keeping the
security services as first-class, swappable slots (not helpers buried in the harness)
is what makes those labs expressible: a challenge breaks exactly one component and
leaves everything else correct.

## The agent loop (ModelSession → ModelTurn)

The model is modelled as a **session**, not a one-shot planner. `Harness.run_session`
drives it:

```
loop:  compile context → session.next(messages, tools, state) → ModelTurn
       for each proposed tool_call:  executor.execute_plan → broker.run_step (the gate)
       feed the observation back;  stop on a final turn or Constraints.max_actions
```

The model only ever **proposes** `ToolCall`s — authority is still conferred by the
harness in `ActionBroker.run_step` (resolve → envelope → authorize → …). The gate and
all invariants (INV-01…14) are unchanged by this abstraction.

The **deterministic** session (`ScriptedSession` over `DeterministicModel`/
`ContextActionModel`, loaded from `plans.yaml`) is the **CI oracle**: it replays the
scripted plan as a single turn's tool calls (so the executor slot — which DVAH-001
breaks by authorizing once then executing the rest — still runs the whole plan in one
`execute_plan` call). Live model sessions (Anthropic/OpenAI/Bedrock) plug into the same
loop and instead emit tool calls turn-by-turn, reacting to observations; those paths
stay out of CI (key-gated). This is the seam that carries live models, real
model-backed subagents, and MCP.

### Model-backed subagents (delegation)

A `delegate` step (`harness/agent.py`) spawns a **child session**, not a scripted
recursion. The flow, in order:

```
INV-06 depth budget check  →  INV-02 derive_child (requested ∩ parent ∩ policy)
  →  ctx.child(attenuated identity + caps)  →  [optional] attach child skills
  →  emit `subagent.started` (child, session_id, depth)
  →  Harness.run_session(child_ctx, child_session)   # the child's OWN turn loop
```

The child gets its own identity (`<agent>@d<depth>` session id; Phase 6 promotes this to
a full `ModelIdentity` on the envelope) and may carry its own skills (opt-in via the
delegate step's `child_skills`). In the deterministic oracle the child session replays
its `subplan_task_id` script, so DVAH-002/006 behave identically; a live child reacts
turn-by-turn. Attenuation (INV-02) and the depth budget (INV-06) are enforced **before**
the child starts, and the `run_step` gate is unchanged.

### Scenario as a world (not just a script)

A challenge describes a **world + goal**, layered so the deterministic oracle stays
authoritative:

- `environment/{users,agents,resources}.yaml` seed the simulated world; `plans.yaml` is
  the **deterministic fixture** the `ScriptedSession` replays (unchanged).
- `environment/tasks.yaml` (optional) declares the real **goal prompt** per `task_id`
  (`{task_id: {prompt, agent?}}`) — what a *live* model receives for that task. The
  deterministic path never reads it; if absent, a default is derived from
  `objective.exploit`/`title`. Surfaced as `loaded.tasks` / `loaded.task_prompt(task_id)`.
- `agents.yaml` may declare non-root agents as **world objects** (`agents:` list/map of
  `{agent_id, capabilities, delegation, skills}`), surfaced as `loaded.agents` for the
  live/subagent path. Deterministic delegation still sources caps from plan-step params,
  so existing labs are unaffected.

So the *world* is shared; the *live* run gets a goal prompt and decides the path, while
the *deterministic* run replays the fixture — same security verdict either way.

### In-app live run + credentials

`POST /api/sessions/{id}/live-run` runs a session through a real model in the web app
(opt-in, billable). It builds a `ModelSession` via `build_model_session(selection, …,
get_key=SETTINGS.api_key)` and returns the agent-timeline trace + `dual_score` (same shape
as `/trace`, so the UI reuses its renderers). It is **key-gated** — 400 unless a key is
configured for the resolved provider — and only runs on explicit request; the deterministic
oracle is appended as the fallback, so a missing SDK/bad key degrades to it (emitting
`model.fallback`) rather than failing the run. The Settings key store (incl. the Bedrock
bearer token) now feeds **both** the tutor and the live path — `_build_live` forwards
`api_key=` to the adapter, and a bare provider name (`anthropic|openai|bedrock`) resolves
directly through profiles. (The tutor **Test** endpoint returns a structured `{ok,error}`
result rather than a 502, and the Bedrock prose path now scopes the bearer token around
`converse` — previously it didn't, which failed auth even with a valid key.)

### Skills as runtime objects (INV-07)

A skill (`dvah/models/skill.py` `SkillManifest`) is a runtime object, not just permission
metadata: it carries a `version`/`digest`, an `instructions` fragment, contributed `tools`,
and *declared* requirements (`permissions`, `mcp`, `network`, `secrets`). **Requesting is
not granting.** Loading is an explicit step — `Harness.attach_skill(ctx, skill,
approved_permissions, pinned_digest)`:

1. runs the `skill_loader` slot (`BuiltinSkillLoader`): `granted = requested ∩ approved`,
   only when the digest is pinned; `expanded = requested − approved` is flagged and sets
   `requires_reapproval`.
2. bounds the result by the host agent's own caps (a skill can never widen its agent), and
3. on a **trusted, non-expanding** load, attaches the skill to the `RunContext` so the
   context compiler injects its instruction fragment + tool schemas on the *trusted*
   INSTRUCTION channel (INV-06 stays clean); an expanded/untrusted upgrade is **not**
   attached and awaits re-approval.

Every load emits a `skill.loaded` trace event (`skill`, `version`, `granted`, `expanded`,
`trusted`, `requires_reapproval`). This is opt-in: the 13 non-skill labs declare no skills,
so `ctx.skills` is empty and their compiled context is unchanged. DVAH-009 is the lab: a
v1.2→v1.3 "helpful upgrade" whose manifest quietly requests more — the vulnerable loader
grants it, the fixed loader keeps `granted ⊆ approved` and requires re-approval.

### Tool router / gateway (native + MCP at once)

The harness has a single `tools` slot and the broker calls one `cfg.tools.invoke(...)`.
`ToolRouter` (`dvah/providers/router.py`) multiplexes several sub-providers under that slot,
dispatching each operation to the first sub-provider whose `supports(namespace)` is true — so
a lab can use native in-process tools **and** a real MCP subprocess boundary together
(`_build_tools(transport="router", …)` composes `NativeToolProvider` + `MCPToolProvider`).

INV-14 stays correct because external-ness is resolved **per-namespace**: the router exposes
`is_external_for(namespace)` / `provider_for(namespace)`, and the broker consults that for the
op it just ran (falling back to the flat `is_external` for plain providers). A native `files`
result keeps its trust; an `mcp` result that self-declares instruction-level trust is
downgraded to untrusted data. Default labs use a single provider and are unaffected.

### Model profiles, router & identity (fallback)

A lab (or the UI) declares a **profile** — `balanced`/`smart`/`cheap`/`local` — instead of a
hardcoded provider, so security semantics never depend on a specific model
(`dvah/providers/profiles.py`; `DVAH_PROFILE_<NAME>` env overrides map a profile to
`provider:model`). `ModelRouter` (`dvah/providers/router_model.py`) is itself a `ModelSession`
that delegates to the first candidate that doesn't error and, on a provider/build failure,
emits a **`model.fallback`** trace event and advances down the chain — with the deterministic
scripted session always appended as the last-resort fallback and the CI oracle. Live adapters
are built lazily (import-safe), and each one now maps its native tool-calling
(`tool_use` / `tool_calls` / `toolUse`) to `ToolCall`s via a `map_tool_calls` helper.

Every envelope records a `ModelIdentity` (`dvah/models/runtime.py`:
provider/model_id/version/temperature/tool_mode/adapter_version/session_id/fallback_chain).
Only the coarse `RuntimeContext.model` **provider label** feeds `action_hash`; the richer
identity is observability-only and never perturbs the hash — so recording *which* model
proposed an action can't change the action's semantic identity.

### Run modes, record/replay & dual scoring

Three execution modes share the same gate:

- **deterministic** (default, CI oracle) — replays `plans.yaml` via the scripted session.
- **live** — `dvah run <lab> <task> --model <provider|profile>` builds a live session through
  the `ModelRouter` (lazy, key-gated; degrades to deterministic if unconfigured).
- **replay** — `dvah run … --record <file>` serializes the normalized `ModelTurn`s + the
  trace + verdict; `dvah replay <file>` re-runs feeding those turns through a `ReplaySession`
  (`dvah/replay.py`) with **no model calls**, reproducing the same verdict.

The **agent timeline** adds informational trace events (`user.task`, `model.request`,
`model.response`, `tool.proposed`, `observation.received`, `agent.finished`, plus
`skill.loaded`/`subagent.started`/`model.fallback`). They carry no `action_hash`, so INV-01
occurrence accounting is untouched.

**Two independent scores** (`dvah/scoring.py`):
- **Runtime Security** — deterministic, model-independent: did anything execute without
  authorization (complete mediation, INV-01)? A property of the *harness*.
- **Live Agent Exercise** — from the trace: did the model attempt the dangerous action, get
  blocked, recover, or avoid it? A property of the *model's behavior* on one run.

They are deliberately separate: a model that avoids the bait does **not** make the
architecture secure, so when a live run doesn't exercise the vulnerable path the UI/CLI can
still run `deterministic_security(...)` — the authoritative verifier that replays the scripted
exploit. Optional `live_experience` scenario metadata (`attack_likelihood`, `expected_paths`)
sets expectations without making the security verdict depend on any model.

### Workspace read-only context (grouped editor tabs)

All read-only context lives in the editor as grouped, lock-badged tabs — never on the side —
so it's obvious what each file is and that you only edit one of them. `web/components/editor-panel.tsx`
groups tabs into **Patch this** (the editable `vulnerable/*.py`, accent-highlighted), **The world ·
read-only** (the `environment/*.yaml` the runtime runs against), and **Harness reference · read-only**
(the `dvah.*` modules the code imports — the challenge briefing's `references`, merged in from the
challenge detail). The harness-reference group is collapsed by default behind a "Reference files"
toggle to keep the file you patch front-and-center. The briefing panel no longer carries a separate
"Runtime reference" section.

### Guided auto-solve demo (`?demo=1`)

The Learn page opens with an entry-level "what is an agent harness?" explainer (the harness
is the layer that sits between the model and the world and confers authority on every action).
For onboarding, the DVAH-001 workspace accepts `?mode=learn&demo=1`, which runs a hands-off,
narrated auto-solve (`web/components/guided-demo.tsx`): it runs the exploit (red board + the
INV-01 timeline), applies the reference fix (fetched from the solution, renamed to keep the
scenario's slot class so the import still resolves) and re-runs the security markers to a green
board. It is fully deterministic — no model — and reuses the run/trace/board components; the
captions come from the challenge `walkthrough.yaml`.

## Grader trust domains (self-study vs assessment)

The web UI runs learner-edited code, so *where* the hidden tests and reference solution
live matters. Two modes (`DVAH_GRADER`):

- **`inprocess`** (default, self-study) — the session is a full copy of the challenge
  (`vulnerable/` + `tests/` + `solution/`); the suite runs in place. Fast, but the
  solution is on disk (only hidden from the file API), so learner-executed code could
  read it. Fine for local single-user practice.
- **`isolated`** (assessment/CTF) — the learner session contains **only** `vulnerable/`
  (+ `environment/` + `scenario.yaml`); it has neither `tests/` nor `solution/`. Grading
  happens out of band (`dvah/grading/`): a throwaway workspace is assembled from the
  *pristine* challenge tests plus the code under test, run through the same sandboxed
  runner (`DockerRunner` recommended). The reference `solution/` is copied in **only** for
  explicit `--solution` reference runs, so it never coexists with learner-controlled code.

- **`rpc`** (fullest split) — closes the one residual of `isolated`: there, the learner's
  code still executes in the *same interpreter* as the hidden `tests/` during grading. In
  `rpc` mode the learner's harness runs in a **separate process** (`dvah/grading/rpc.py`
  `AdapterServer`, started via `python -m dvah.grading.rpc <workspace>`) whose workspace has
  **no `tests/` and no `solution/`** at all; the grader process drives the invariant battery
  (`run_battery`) against an `RpcAdapter` that marshals each `HarnessAdapter` call over stdio
  JSON. So the hidden assertions live only in the grader — the learner's code never sees the
  tests or the solution. This grades the invariant **security oracle** (per-invariant
  verdict); the per-tier pytest grading (functional/exploit/…) still uses the `isolated`
  assembly path. Opt-in (returns a per-invariant verdict, not the UI's per-tier report).

This separates the two trust domains: the learner's editing/execution environment and the
grader's hidden material. For real competitions/assessments, pair `isolated`/`rpc` with a
private challenge source (the public repo ships reference solutions).

## Test taxonomy

- `unit` / `integration` — `tests/`, run in CI.
- `functional` / `exploit` / `invariant` / `adversarial` — per challenge, run via
  `dvah test <lab>` (and against `--solution` in CI to prove the reference).
- `e2e` — `tests/e2e/`, real HTTP services, **manual only** (excluded from CI by the
  `-m 'not e2e'` default).
