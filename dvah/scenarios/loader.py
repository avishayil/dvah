"""Load a challenge into a runnable Harness.

Builds the correct default HarnessConfig, seeds the simulated services from the
challenge's ``environment/`` files, then replaces the named slots with the challenge's
``vulnerable/`` (or ``solution/``) implementations via ``module:Class`` references.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..artifacts import (
    builtin_catalog,
    load_agent,
    load_catalog_file,
    load_prompts,
    load_resources,
    load_skill,
    load_workflows,
    overlay,
)
from ..harness.config import HarnessConfig
from ..harness.context import RunContext
from ..models.agent import AgentDefinition
from ..models.skill import SkillManifest
from ..harness.executor import BuiltinExecutor
from ..harness.loop import Harness
from ..models.capability import Capability, CapabilitySet
from ..models.envelope import Intent
from ..models.identity import Actor, DelegationChain, Principal
from ..models.runtime import Constraints, ModelIdentity, RuntimeContext
from ..harness.compiler import BuiltinContextCompiler
from ..observability.trace import TraceLog
from ..providers.native_tools import NativeToolProvider
from ..providers.reactive import ContextActionModel
from ..security.approvals import BuiltinApprovalService
from ..security.budget import BuiltinBudgetTracker
from ..security.capabilities import BuiltinCapabilityResolver
from ..security.policy import BuiltinPolicy
from ..security.provenance import BuiltinProvenanceTracker
from ..security.secrets import BuiltinSecretBroker
from ..services.memory import FileStore, GithubStore


@dataclass(frozen=True)
class LoadedChallenge:
    harness: Harness
    root_ctx: RunContext
    files: FileStore
    github: GithubStore
    trace: TraceLog
    # v0.3 "scenario world" metadata (additive; the deterministic path ignores it and
    # replays plans.yaml). Live sessions in later phases consume the task prompt + agents.
    tasks: dict = field(default_factory=dict)  # task_id -> {prompt, agent?, ...}
    agents: dict = field(default_factory=dict)  # agent_id -> {capabilities, delegation, skills}
    default_prompt: str = ""
    # v0.3 "artifacts as files" metadata (additive; deterministic path ignores it).
    # skills: role/name -> SkillManifest (from skills/**/SKILL.md, else environment/skills.yaml).
    skills: dict = field(default_factory=dict)
    # agent_defs: agent_id -> AgentDefinition (from agents/*.md, else synthesized from root).
    agent_defs: dict = field(default_factory=dict)
    # tools_catalog: "namespace.action" -> ToolSpec (core catalog + optional lab overlay).
    tools_catalog: dict = field(default_factory=dict)
    # resources: id -> Resource (agent-facing knowledge; advisory, deterministic path ignores).
    resources: dict = field(default_factory=dict)
    # workflows: task_id -> Workflow (descriptive view of plans.yaml; not executed).
    workflows: dict = field(default_factory=dict)
    # prompts: agent_id -> PromptStack (layered system→agent→skill→task; live path only).
    prompts: dict = field(default_factory=dict)
    # Optional live-mode metadata (additive): {attack_likelihood, expected_paths}. It
    # describes what a REAL model *might* do; the deterministic security verdict never
    # depends on it, so labs stay model-independent.
    live_experience: dict = field(default_factory=dict)

    def task_prompt(self, task_id: str) -> str:
        """The real goal prompt for a task (from tasks.yaml), else the scenario default.

        This is metadata for the live agent path; deterministic runs still replay the
        scripted plans.yaml keyed by task_id and never read this.
        """
        entry = self.tasks.get(task_id)
        if isinstance(entry, dict) and entry.get("prompt"):
            return entry["prompt"]
        return self.default_prompt


def _cap_set(raw: list[dict] | None) -> CapabilitySet:
    return CapabilitySet(caps=frozenset(Capability(**c) for c in (raw or [])))


def _load_slot(challenge_dir: Path, ref: str, prefix: str):
    """Load ``module.path:Class`` from a file under the challenge dir.

    Uses a per-(challenge, mode, slot) unique module name and never touches
    ``sys.path``/``sys.modules``, so multiple challenges — and both vulnerable and
    solution modes — can coexist in one process (needed by the adversarial grader).
    """
    module_ref, class_name = ref.split(":")
    file_path = challenge_dir / (module_ref.replace(".", "/") + ".py")
    module_name = f"{prefix}_{module_ref.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {ref} from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, class_name)()


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) if path.exists() else {}


def _default_prompt(spec: dict) -> str:
    """A reasonable live-agent goal prompt derived from the scenario when no
    tasks.yaml is supplied — so every lab has a usable prompt without one."""
    objective = spec.get("objective") or {}
    return objective.get("exploit") or spec.get("title") or spec.get("id", "")


def _load_agents(agents_yaml: dict) -> dict:
    """Collect declared agents as world objects, keyed by agent_id. Tolerant of the
    legacy shape (only ``root:``) and an optional ``agents:`` list/map of subagents.
    Exposed on the LoadedChallenge for the live/subagent path; the deterministic
    delegate path still reads caps from plan-step params, so existing labs are
    unaffected."""
    declared: dict = {}
    root = agents_yaml.get("root")
    if isinstance(root, dict) and root.get("agent_id"):
        declared[root["agent_id"]] = root
    extra = agents_yaml.get("agents")
    if isinstance(extra, list):
        for a in extra:
            if isinstance(a, dict) and a.get("agent_id"):
                declared[a["agent_id"]] = a
    elif isinstance(extra, dict):
        for aid, a in extra.items():
            if isinstance(a, dict):
                declared[aid] = {"agent_id": aid, **a}
    return declared


def _manifest_from_yaml(name: str, variant: dict) -> SkillManifest:
    """Bridge the legacy ``environment/skills.yaml`` variant shape into a SkillManifest."""
    return SkillManifest(
        name=name,
        digest=str(variant.get("digest", "")),
        permissions=tuple(Capability(**c) for c in (variant.get("permissions") or [])),
        version=str(variant.get("version", "")),
        description=str(variant.get("description", "")),
        instructions=str(variant.get("instructions", "")),
        tools=tuple(variant.get("tools") or ()),
        mcp=tuple(variant.get("mcp") or ()),
        network=tuple(variant.get("network") or ()),
        secrets=tuple(variant.get("secrets") or ()),
    )


def _load_skills(challenge_dir: Path, env_dir: Path) -> dict:
    """Load a lab's skills as SkillManifests keyed by role/name.

    Prefers file-based artifacts (``skills/registry.yaml`` naming ``role -> dir`` with a
    ``skills/<dir>/SKILL.md`` each). Falls back to the legacy ``environment/skills.yaml``
    (``name -> {role -> variant}``) so a lab can migrate incrementally. Empty when neither
    exists — most labs declare no skills.
    """
    registry = challenge_dir / "skills" / "registry.yaml"
    if registry.exists():
        roles = yaml.safe_load(registry.read_text()) or {}
        return {
            role: load_skill(challenge_dir / "skills" / dirname / "SKILL.md")
            for role, dirname in roles.items()
        }
    legacy = _read_yaml(env_dir / "skills.yaml")
    manifests: dict = {}
    for name, variants in legacy.items():
        if isinstance(variants, dict):
            for role, variant in variants.items():
                if isinstance(variant, dict):
                    manifests[role] = _manifest_from_yaml(name, variant)
    return manifests


def _load_agent_defs(challenge_dir: Path, agents_yaml: dict) -> dict:
    """Load ``agents/*.md`` into AgentDefinitions keyed by agent_id. When a lab ships no
    agent files, synthesize a default from the ``agents.yaml`` root so every lab exposes a
    definition (opt-in like tasks.yaml — no lab is forced to author one)."""
    agents_dir = challenge_dir / "agents"
    if agents_dir.is_dir():
        defs = {}
        for md in sorted(agents_dir.glob("*.md")):
            agent = load_agent(md)
            defs[agent.agent_id] = agent
        if defs:
            return defs
    root = agents_yaml.get("root") or {}
    agent_id = root.get("agent_id", "root-agent")
    return {
        agent_id: AgentDefinition(
            agent_id=agent_id,
            capabilities=tuple(Capability(**c) for c in (root.get("capabilities") or [])),
        )
    }


def _load_tools_catalog(env_dir: Path) -> dict:
    """The core provider-shared catalog, optionally overlaid by a per-lab tools.yaml."""
    catalog = dict(builtin_catalog())
    lab_tools = env_dir / "tools.yaml"
    if lab_tools.exists():
        catalog = overlay(catalog, load_catalog_file(lab_tools))
    return catalog


def _build_tools(transport: str, files: FileStore, github: GithubStore):
    if transport == "http":
        from ..providers.http_tools import HttpToolProvider  # lazy: needs httpx + services

        return HttpToolProvider()
    if transport == "router":
        # Multiplex native (files/github) + a real MCP subprocess boundary under one slot,
        # so a lab can use both at once. The broker applies INV-14 trust per-namespace.
        from ..providers.mcp_tools import MCPToolProvider
        from ..providers.router import ToolRouter

        return ToolRouter(
            (NativeToolProvider(files=files, github=github), MCPToolProvider())
        )
    return NativeToolProvider(files=files, github=github)


def load_challenge(
    challenge_dir: str | Path,
    use_solution: bool = False,
    transport: str = "native",
) -> LoadedChallenge:
    challenge_dir = Path(challenge_dir).resolve()
    spec = yaml.safe_load((challenge_dir / "scenario.yaml").read_text())

    env_dir = challenge_dir / "environment"
    resources = _read_yaml(env_dir / "resources.yaml")
    users = _read_yaml(env_dir / "users.yaml")
    agents = _read_yaml(env_dir / "agents.yaml")

    files = FileStore(seed=resources.get("files", {}))
    github = GithubStore(seed=resources.get("github", {}))
    trace = TraceLog()
    model = ContextActionModel.from_yaml(env_dir / "plans.yaml")
    constraints = Constraints(**spec.get("constraints", {}))

    slots = {
        "model": model,
        "policy": BuiltinPolicy(),
        "approvals": BuiltinApprovalService(),
        "capabilities": BuiltinCapabilityResolver(),
        "provenance": BuiltinProvenanceTracker(),
        "secrets": BuiltinSecretBroker(credentials=resources.get("secrets", {})),
        "tools": _build_tools(transport, files, github),
        "executor": BuiltinExecutor(),
        "trace": trace,
        "constraints": constraints,
        "context_compiler": BuiltinContextCompiler(),
        "budget": BuiltinBudgetTracker(limit=constraints.max_actions),
    }
    prefix = f"_dvah_{spec['id']}_{'sol' if use_solution else 'vuln'}"
    override_key = "solution_overrides" if use_solution else "overrides"
    for slot, ref in (spec.get(override_key) or {}).items():
        slots[slot] = _load_slot(challenge_dir, ref, prefix)

    cfg = HarnessConfig(**slots)
    root_ctx = _build_root_ctx(spec, users, agents)
    tasks = _read_yaml(env_dir / "tasks.yaml") or {}
    agent_defs = _load_agent_defs(challenge_dir, agents)
    return LoadedChallenge(
        harness=Harness(cfg),
        root_ctx=root_ctx,
        files=files,
        github=github,
        trace=trace,
        tasks=tasks,
        agents=_load_agents(agents),
        default_prompt=_default_prompt(spec),
        live_experience=spec.get("live_experience") or {},
        skills=_load_skills(challenge_dir, env_dir),
        agent_defs=agent_defs,
        tools_catalog=_load_tools_catalog(env_dir),
        resources=load_resources(challenge_dir),
        workflows=load_workflows(challenge_dir),
        prompts=load_prompts(challenge_dir, agent_defs, tasks),
    )


def _build_root_ctx(spec: dict, users: dict, agents: dict) -> RunContext:
    principal = Principal(**users.get("principal", {"user": "alice", "tenant": "acme"}))
    root_agent = agents.get("root", {})
    agent_id = root_agent.get("agent_id", "root-agent")
    provider = spec.get("model", {}).get("provider", "deterministic")
    constraints = Constraints(**spec.get("constraints", {}))
    return RunContext(
        principal=principal,
        actor=Actor(agent_id=agent_id, instance_id=f"{agent_id}-inst"),
        delegation=DelegationChain(root_principal=principal.user, chain=(agent_id,), depth=0),
        intent=Intent(task_id=spec["id"], purpose=spec.get("title", "")),
        capabilities=_cap_set(root_agent.get("capabilities")),
        constraints=constraints,
        runtime=RuntimeContext(
            model=provider,
            model_identity=ModelIdentity(provider=provider, session_id=f"{spec['id']}-root"),
        ),
    )
