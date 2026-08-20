# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this is

DVAH (Damn Vulnerable Agent Harness) is a **patch-the-runtime security lab** for AI-agent
platforms. Learners exploit an architectural failure in an intentionally-insecure agent
runtime, trace it, identify the broken **invariant** (INV-01…12), patch the harness in
place, and prove the fix holds against functional/exploit/invariant/**adversarial** tests.

Core idea: **plans propose; the frozen `ActionEnvelope` carries authority.** Every
side-effectful operation is resolved into one envelope immediately before execution, and
authorization/approval/capabilities/provenance/secrets all bind to that envelope.

## Repository map

- `dvah/models/` — pure **frozen** Pydantic data (`ActionEnvelope` + parts, plus the
  reference primitives `Resource`, `Workflow`, `PromptStack`). No behavior.
- `dvah/guardrails/` — first-class, **swappable** security services (policy, approvals,
  capabilities, budget, secrets, provenance, revocation, skills, decision); each is a
  `Protocol` + a correct `Builtin*` default. Challenges override these with broken versions.
  (Renamed from `dvah/security/`, which stays as a re-export compat shim — to be removed later.)
- `dvah/memory/` — agent memory (`store.py`; reference Memory layer). World state lives in
  `dvah/services/world_state.py` (FileStore/GithubStore). Both keep compat shims at their old
  paths (`dvah/services/memory_store.py`, etc.).
- `dvah/resources/`, `dvah/workflows/`, `dvah/prompts/` — thin domain homes over the new
  `Resource`/`Workflow`/`PromptStack` models + parsers; `dvah/schemas/` is a dependency-free
  output-schema validator. All advisory — never reaches `action_hash`.
- `dvah/harness/` — runtime plumbing: `broker.py` (the authorize→approve→execute gate),
  `executor.py`, `agent.py` (delegation), `context.py` (`RunContext`), `loop.py`
  (`Harness.run_session` drives the agent loop: `ModelSession.next → ModelTurn`, then each
  proposed `ToolCall` runs through the executor slot + the `run_step` gate). The
  deterministic `ScriptedSession` (over `plans.yaml`) is the CI oracle; live model
  sessions plug into the same loop and stay out of CI. Skills are runtime objects
  (`models/skill.py`: instructions/tools/requested-perms/digest); `Harness.attach_skill`
  runs the `skill_loader` slot (`granted = requested ∩ approved`, requesting≠granting,
  INV-07), injects a trusted skill's instructions into the compiled context, and emits
  `skill.loaded` — opt-in, so non-skill labs are unchanged.
- `dvah/providers/` — `ModelProvider`/`ModelSession` (deterministic, anthropic, openai,
  bedrock) and `ToolProvider` (native in-process, http, MCP subprocess, and `ToolRouter`
  which multiplexes them by `supports()` with per-namespace INV-14 external-ness). SDKs are
  **lazy-imported** (import-safe). `profiles.py` maps a `balanced`/`smart`/`cheap`/`local`
  profile → provider; `router_model.py` `ModelRouter` selects a session with a
  `model.fallback` chain (deterministic = last resort + CI oracle). Model identity is
  recorded as `ModelIdentity` on the envelope but only the provider label reaches
  `action_hash`.
- `dvah/artifacts/` — dependency-free parsers that turn real-world artifact files into the
  frozen models (Anthropic/Claude Code conventions, cross-ref MCP): `frontmatter.py`
  (`---` YAML splitter), `skill_md.py` (`load_skill` → `SkillManifest` from a `SKILL.md`),
  `agent_md.py` (`load_agent` → `AgentDefinition` from `agents/<id>.md`), `tool_catalog.py`
  (`builtin_catalog`/`load_catalog_file`/`overlay`).
- `dvah/tools/catalog/*.yaml` — the core, provider-shared tool catalog (files, github,
  email, cloud, mcp): one `ToolSpec` per `namespace.action` the providers implement, with
  `input_schema` aligned to MCP's `inputSchema`. Advisory only — never reaches `action_hash`.
- `dvah/mutation/` — the chaos engine: per-invariant "defeat" probes.
- `dvah/webapi/` — FastAPI app wrapping the harness for the web UI (sessions, sandboxed
  runner, trace, hints, mutate, settings, optional tutor, and an opt-in key-gated
  `/live-run` that drives a real model). Settings expose one generic **Model & API** key
  (shared by tutor + live) and a **single global run mode** (`deterministic` default | `live`)
  — not a per-lab chooser; `settings.run_mode` + `settings.model.*` in the API view.
- `dvah/grading/` — out-of-process grading. `DVAH_GRADER` selects the mode: `inprocess`
  (default, self-study; full copy), `isolated` (assessment; learner session is
  vulnerable-only, graded in a throwaway workspace), or `rpc` (fullest split; learner code
  runs in a separate `AdapterServer` process with no tests/solution, grader drives the
  invariant battery over stdio via `RpcAdapter`). See `docs/ARCHITECTURE.md`.
- `dvah/scenarios/loader.py` + `catalog.py` — load a challenge into a runnable harness by
  swapping named slots with the challenge's `vulnerable/` or `solution/` code. The
  `LoadedChallenge` also exposes `.skills` (role/name → `SkillManifest`), `.agent_defs`
  (agent_id → `AgentDefinition`), `.tools_catalog` (id → `ToolSpec`), `.resources` (id →
  `Resource`), `.workflows` (task_id → descriptive `Workflow`), and `.prompts` (agent_id →
  `PromptStack`), parsed from the file-based artifacts below.
- `challenges/DVAH-00N-*/` — the labs (`scenario.yaml`, `README.md`, `vulnerable/`, hidden
  `solution/`, `environment/*.yaml`, `tests/`, `walkthrough.yaml`).
- `services/` — FastAPI mock external systems; `web/` — Next.js browser IDE.

## Commands

```bash
# Python
uv venv && uv pip install -e ".[dev,services,web]"
uv run pytest tests/ -m "unit or integration"          # CI set (e2e excluded by default)
uv run pytest tests/e2e -m e2e                          # manual e2e only
uv run dvah list|start|test|trace|mutate
uv run dvah run <lab> <task> [--model <provider|profile>] [--record f.json]  # agent loop + 2 scores
uv run dvah replay f.json                               # re-run a recording, no model calls

# every lab's reference solution (should be green)
make labs

# Frontend
cd web && npm install && npm test && npm run build

# Full stack
docker compose up --build                               # web :3000 + api :8000
docker compose --profile services up --build            # + mock services :8001-8004
```

## Conventions (match these)

- **Immutability**: models are `frozen=True`; update via `model_copy`/`replace`, never
  mutate. `RunContext` is threaded, copy-on-write.
- **Small files** (~150 lines), organized by feature; `models/` = data, `guardrails/` +
  `harness/` = behavior. The harness/guardrails split is load-bearing — several labs are
  "the check was put in the wrong component."
- **Test markers**: `unit`, `integration` (CI), `functional`/`exploit`/`invariant`/
  `adversarial` (per lab), `e2e` (manual, excluded via `-m 'not e2e'`). 80% coverage gate
  on `dvah`.
- Invariant tests are tagged with their invariant id (`@pytest.mark.invariant("INV-0X")`)
  so the web UI's invariant board maps results per-invariant.

## Adding a lab (pattern)

1. Copy the DVAH-001/002 shape: `scenario.yaml` (declare `overrides` +
   `solution_overrides` for the one broken slot + its declared `invariants`), `README.md`,
   `vulnerable/`, `solution/`, `environment/{users,agents,resources,plans}.yaml`, and
   `tests/{test_functional,test_exploit,test_invariants,test_adversarial}.py`. Every lab now
   also ships an authored `agents/<root>.md` (AgentDefinition — frontmatter
   name/description/model/tools/capabilities/delegation + system-prompt body) and a
   `prompts/system.md` base instruction layer as standard; DVAH-009 additionally ships a
   `skills/` package (`SKILL.md` + `registry.yaml`).
2. Author `walkthrough.yaml` (tiers nudge→concept→pointer→solution + guided `steps`).
3. Verify: vulnerable = red on exploit+invariant(+adversarial), `--solution` = all green.

**Scenario as a world (v0.3, all optional/additive):** a lab describes a *world + goal*,
not only a script. `environment/*.yaml` seeds the world; `plans.yaml` is the
**deterministic fixture** the CI oracle (`ScriptedSession`) replays — keep it as-is.
Optionally add:
- `environment/tasks.yaml` — real goal prompts keyed by the same `task_id` as `plans.yaml`
  (`{task_id: {prompt, agent?}}`). The live agent path uses the prompt; the deterministic
  path ignores it. If absent, a default prompt is derived from `objective.exploit`/`title`.
  Exposed as `loaded.tasks` + `loaded.task_prompt(task_id)`.
- `agents.yaml` beyond `root:` — declare non-root agents as world objects (an `agents:`
  list/map of `{agent_id, capabilities, delegation:{allowed,max_depth}, skills}`). Exposed
  as `loaded.agents` for the live/subagent path; the deterministic `delegate` still reads
  caps from plan-step params, so existing labs are unaffected.
- **Model-backed subagents** — `delegate` (`harness/agent.py`) attenuates caps (INV-02) +
  checks the depth budget (INV-06), then spawns a **child `ModelSession`** that runs its own
  `run_session` loop with its own identity (`<agent>@d<depth>`) and optional `child_skills`
  (opt-in via the delegate step). Emits `subagent.started`. Deterministic children replay
  their `subplan_task_id` script, so DVAH-002/006 are byte-identical; the gate is unchanged.
- **File-based artifacts** — a lab may ship skills as `skills/<name>/SKILL.md` files plus a
  `skills/registry.yaml` (role → dir) instead of the legacy `environment/skills.yaml`, and
  declare agents as `agents/<id>.md` (Claude Code subagent frontmatter + system-prompt body).
  These parse into `loaded.skills` / `loaded.agent_defs` via `dvah/artifacts/`; the tool
  catalog defaults to `builtin_catalog()` and can be overlaid per-lab with
  `environment/tools.yaml`. All of it is advisory metadata for the live/subagent path.

## Gotchas

- Adapters must import without their SDK installed (keep imports lazy inside methods).
- The lab runner shells out to `pytest`, so **pytest is a runtime dependency** of the
  `webapi` image (not just dev).
- e2e and live-model paths must stay out of CI.
- An authored `agents/<id>.md`'s `capabilities` must **equal** the `agents.yaml` root caps —
  a test enforces this. Artifact metadata (`description`, system-prompt bodies,
  `input_schema`) is advisory and must **never** affect authorization or `action_hash`.
- Deployment target is **local single-user**; auth/rate-limiting/network isolation are a
  documented pre-hosting track, not yet implemented.
