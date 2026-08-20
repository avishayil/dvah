"""Unit tests for the reference-architecture primitive models added in Phase 1."""

import pytest

from dvah.artifacts.tool_catalog import builtin_catalog
from dvah.models.prompt import PromptLayer, PromptScope, PromptStack
from dvah.models.resource import Resource
from dvah.models.tool_spec import SideEffect, ToolSpec
from dvah.models.workflow import Driver, StepKind, Workflow, WorkflowStep
from dvah.security.policy import DEFAULT_APPROVAL_ACTIONS, approval_actions_from_catalog


@pytest.mark.unit
def test_resource_defaults_to_untrusted_data():
    from dvah.models.provenance import TrustLevel

    r = Resource(id="github:acme/app#1")
    assert r.trust == TrustLevel.UNTRUSTED_DATA
    assert r.mime_type == "text/plain"


@pytest.mark.unit
def test_prompt_stack_renders_in_canonical_order():
    stack = PromptStack(layers=(
        PromptLayer(scope=PromptScope.TASK, text="do the thing"),
        PromptLayer(scope=PromptScope.SYSTEM, text="be safe"),
        PromptLayer(scope=PromptScope.SKILL, text=""),  # empty layers skipped
        PromptLayer(scope=PromptScope.AGENT, text="you triage"),
    ))
    assert stack.render() == "be safe\n\nyou triage\n\ndo the thing"


@pytest.mark.unit
def test_workflow_is_frozen_descriptive_shape():
    wf = Workflow(id="w1", driver=Driver.CODE, steps=(
        WorkflowStep(id="s1", kind=StepKind.TOOL, namespace="files", action="read", next=("s2",)),
        WorkflowStep(id="s2", kind=StepKind.DELEGATE),
    ))
    assert wf.steps[0].driver == Driver.CODE
    assert wf.steps[0].next == ("s2",)


@pytest.mark.unit
def test_tool_spec_governance_fields_default_safe():
    spec = ToolSpec(namespace="files", action="read")
    assert spec.side_effect == SideEffect.READ
    assert spec.requires_approval is False
    assert spec.output_schema == {}
    assert spec.timeout_s is None


@pytest.mark.unit
def test_catalog_approval_flags_mirror_the_policy_constant():
    """The catalog's requires_approval flags must equal the gate's frozen approval set."""
    assert approval_actions_from_catalog(builtin_catalog()) == DEFAULT_APPROVAL_ACTIONS


@pytest.mark.unit
def test_destructive_actions_are_flagged_in_catalog():
    catalog = builtin_catalog()
    assert catalog["files.delete"].side_effect == SideEffect.DESTRUCTIVE
    assert catalog["files.delete"].requires_approval is True
    assert catalog["github.issue.read"].side_effect == SideEffect.READ
