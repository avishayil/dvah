"""Long-tail coverage: loader/catalog internals, broker/agent/compiler branches,
conformance adapters, mutation, settings/hints/invariants, prompt task layer."""

import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.models.operation import Operation
from dvah.models.runtime import Constraints


# ---------------- loader internals ----------------
@pytest.mark.unit
def test_load_slot_bad_ref_raises():
    from dvah.scenarios.loader import _load_slot
    from pathlib import Path
    with pytest.raises((ImportError, FileNotFoundError)):
        _load_slot(Path("challenges/DVAH-001-plan-time-authorization"),
                   "guardrails.vulnerable.nonexistent:Nope", "_probe")


@pytest.mark.unit
def test_load_skills_legacy_yaml(tmp_path):
    from dvah.scenarios.loader import _load_skills
    env = tmp_path / "environment"
    env.mkdir()
    (env / "skills.yaml").write_text(
        "gh:\n  approved:\n    digest: v1\n    permissions:\n      - {namespace: github, action: issue.read}\n"
    )
    skills = _load_skills(tmp_path, env)
    assert skills["approved"].digest == "v1"


@pytest.mark.unit
def test_load_agent_defs_synthesized(tmp_path):
    from dvah.scenarios.loader import _load_agent_defs
    defs = _load_agent_defs(tmp_path, {"root": {"agent_id": "solo",
                                                 "capabilities": [{"namespace": "files", "action": "read"}]}})
    assert defs["solo"].capabilities == (Capability(namespace="files", action="read"),)


@pytest.mark.unit
def test_load_tools_catalog_overlay(tmp_path):
    from dvah.scenarios.loader import _load_tools_catalog
    (tmp_path / "tools.yaml").write_text(
        "- {namespace: files, action: read, name: custom_read, description: overridden}\n"
    )
    cat = _load_tools_catalog(tmp_path)
    assert cat["files.read"].name == "custom_read"


# ---------------- catalog helpers ----------------
@pytest.mark.unit
def test_catalog_containment_helpers(tmp_path):
    from dvah.scenarios import catalog
    from pathlib import Path
    with pytest.raises(LookupError):
        catalog._ensure_contained(tmp_path)  # outside challenges/
    assert catalog._within_challenges(catalog.CHALLENGES_DIR / "DVAH-001-plan-time-authorization")
    assert not catalog._within_challenges(tmp_path)
    # resolve by absolute path of a real challenge
    d = catalog.CHALLENGES_DIR / "DVAH-001-plan-time-authorization"
    assert catalog.resolve_challenge(str(d)) == d.resolve()


@pytest.mark.unit
def test_catalog_iter_skips_malformed(tmp_path, monkeypatch):
    from dvah.scenarios import catalog
    (tmp_path / "not-a-dir.txt").write_text("x")
    (tmp_path / "no-scenario").mkdir()
    bad = tmp_path / "DVAH-XX"; bad.mkdir(); (bad / "scenario.yaml").write_text(": : bad yaml :")
    good = tmp_path / "DVAH-77"; good.mkdir(); (good / "scenario.yaml").write_text("id: DVAH-77\n")
    monkeypatch.setattr(catalog, "CHALLENGES_DIR", tmp_path)
    catalog._catalog.cache_clear()
    mapping = catalog._catalog()   # skip logic for non-dirs / no-scenario / bad yaml lives here
    assert "DVAH-77" in mapping
    catalog._catalog.cache_clear()


# ---------------- broker branches ----------------
@pytest.mark.unit
def test_broker_approval_mismatch_denies(make_harness, make_ctx):
    from dvah.guardrails.decision import Decision, Denied, Verdict
    from dvah.providers.model import PlanStep

    class NeedsApprovalPolicy:
        def authorize(self, env):
            return Decision(verdict=Verdict.NEEDS_APPROVAL, reason="", invariant="INV-03")

    class RejectingApprovals:
        def find(self, grants, env): return None
        def request(self, env): return object()
        def validate(self, env, grant): return False

    harness, *_ = make_harness(
        scripts={"t": [{"namespace": "files", "action": "delete", "resource": "/x"}]},
        files_seed={"/x": "d"},
        slots={"policy": NeedsApprovalPolicy(), "approvals": RejectingApprovals()},
    )
    ctx = make_ctx(capabilities=CapabilitySet(caps=frozenset({Capability(namespace="files", action="delete")})))
    step = PlanStep(namespace="files", action="delete", resource="/x")
    with pytest.raises(Denied):
        harness.broker.run_step(ctx, step)


@pytest.mark.unit
def test_broker_consumes_one_time_grant(make_harness, make_ctx):
    from dvah.guardrails.decision import Decision, Verdict
    from dvah.providers.model import PlanStep

    consumed = []

    class Grant:
        one_time = True
        approved_action_hash = "h"

    class NeedsApprovalPolicy:
        def authorize(self, env):
            return Decision(verdict=Verdict.NEEDS_APPROVAL, reason="", invariant="INV-03")

    class OneTimeApprovals:
        def find(self, grants, env): return None
        def request(self, env): return Grant()
        def validate(self, env, grant): return True
        def consume(self, grant): consumed.append(grant)

    harness, *_ = make_harness(
        scripts={"t": [{"namespace": "files", "action": "delete", "resource": "/x"}]},
        files_seed={"/x": "d"},
        slots={"policy": NeedsApprovalPolicy(), "approvals": OneTimeApprovals()},
    )
    ctx = make_ctx(capabilities=CapabilitySet(caps=frozenset({Capability(namespace="files", action="delete")})))
    harness.broker.run_step(ctx, PlanStep(namespace="files", action="delete", resource="/x"))
    assert consumed  # the one-time grant was consumed


# ---------------- agent depth + compiler skip ----------------
@pytest.mark.unit
def test_delegate_depth_exceeded(make_harness, make_ctx):
    from dvah.guardrails.decision import Denied
    from dvah.providers.model import PlanStep
    harness, *_ = make_harness(scripts={"t": []})
    ctx = make_ctx(constraints=Constraints(delegation_depth=0))
    step = PlanStep(namespace="agent", action="delegate", resource="",
                    parameters={"child_agent_id": "c", "subplan_task_id": "t"})
    with pytest.raises(Denied):
        harness.delegate(ctx, step)


@pytest.mark.unit
def test_compiler_skips_empty_skill(make_ctx):
    from dvah.harness.compiler import BuiltinContextCompiler
    from dvah.models.skill import SkillManifest
    ctx = make_ctx().with_skill(SkillManifest(name="empty", digest="d"))  # no instructions/tools
    compiled = BuiltinContextCompiler().compile(ctx)
    assert all(i.source != "skill:empty" for i in compiled.items)


# ---------------- conformance adapters + battery ----------------
@pytest.mark.unit
def test_battery_probe_error_is_false():
    from dvah.conformance.battery import run_battery

    class BrokenAdapter:
        name = "broken"
        def __getattr__(self, _):
            raise RuntimeError("boom")

    run = run_battery(BrokenAdapter())
    assert run.holding == 0 and any("probe error" in r.detail for r in run.results)


@pytest.mark.unit
def test_builtin_adapter_external_tool_trust():
    from dvah.conformance.builtin_adapter import BuiltinAdapter
    a = BuiltinAdapter()
    assert a.external_tool_trust("not-a-level") == "untrusted_data"
    assert a.external_tool_trust("trusted_instruction") == "untrusted_data"
    assert a.external_tool_trust("untrusted_data") == "untrusted_data"


@pytest.mark.unit
def test_external_harness_defaults():
    from dvah.conformance.external_adapter import ExternalHarness
    h = ExternalHarness()
    assert h.run_plan(CapabilitySet(), {}, "no-task", 5) is not None   # _leaves -> []
    assert h.compile_context("p", (), ()) is not None
    caps = CapabilitySet(caps=frozenset({Capability(namespace="files", action="read")}))
    assert h.authorize(caps, "files", "read", "/x").allow
    assert h.authorize_attribution("u", "u", ("u",), "u").allow


# ---------------- settings / hints / invariants ----------------
@pytest.mark.unit
def test_settings_key_source_and_run_mode(monkeypatch):
    from dvah.webapi.settings import RuntimeSettings
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    s = RuntimeSettings()
    assert s.key_source("anthropic") is None
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert s.key_source("anthropic") == "env"
    s.update(api_key="x", provider="anthropic")
    assert s.key_source("anthropic") == "ui"
    s.update(run_mode="live")
    assert s.run_mode() == "live"
    with pytest.raises(ValueError):
        s.update(run_mode="bogus")


@pytest.mark.unit
def test_hints_fallback_when_no_tiers(monkeypatch):
    from dvah.webapi import hints
    monkeypatch.setattr(hints, "_walkthrough", lambda d: {})
    idx = hints.hint_index("DVAH-001")
    assert idx["tiers"] and idx["tiers"][0]["level"] == "concept"


@pytest.mark.unit
def test_walkthrough_missing_returns_empty(tmp_path, monkeypatch):
    from dvah.webapi import hints
    assert hints._walkthrough(tmp_path) == {}  # no walkthrough.yaml


@pytest.mark.unit
def test_invariant_statements_parses_doc():
    from dvah.webapi.invariants import invariant_statements
    out = invariant_statements()
    assert any(k.startswith("INV-") for k in out)


# ---------------- prompt task layer + mutation ----------------
@pytest.mark.unit
def test_prompt_includes_task_layer(tmp_path):
    from dvah.artifacts.prompt import load_prompts
    from dvah.models.agent import AgentDefinition
    from dvah.models.prompt import PromptScope
    agent = AgentDefinition(agent_id="runner", name="runner", instructions="be careful")
    tasks = {"t1": {"prompt": "do the job", "agent": "runner"}}
    stacks = load_prompts(tmp_path, {"runner": agent}, tasks)
    scopes = [l.scope for l in stacks["runner"].layers]
    assert PromptScope.TASK in scopes and PromptScope.AGENT in scopes


@pytest.mark.unit
def test_mutation_engine_all_flags():
    from dataclasses import fields
    from dvah.mutation.engine import run
    from dvah.mutation.flags import MutationFlags
    all_on = MutationFlags(**{fld.name: True for fld in fields(MutationFlags)})
    result = run(all_on)
    assert result.total > 0 and result.holding < result.total


@pytest.mark.unit
def test_scoring_deterministic_security_denied_task():
    from dvah.scoring import deterministic_security
    v = deterministic_security("challenges/DVAH-001-plan-time-authorization",
                               "DVAH-001-exploit", use_solution=True)
    assert v.secure is True  # solution denies the unauthorized op
