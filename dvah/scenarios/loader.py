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

from ..harness.config import HarnessConfig
from ..harness.context import RunContext
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
