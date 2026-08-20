"""Unit tests for the dependency-free schema validator + domain-package re-exports."""

import pytest

from dvah.schemas import schema_errors, validate


@pytest.mark.unit
def test_valid_object_passes():
    schema = {"type": "object", "properties": {"body": {"type": "string"}}, "required": ["body"]}
    assert validate(schema, {"body": "hi"})
    assert schema_errors(schema, {"body": "hi"}) == []


@pytest.mark.unit
def test_missing_required_and_wrong_type_reported():
    schema = {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}
    assert "missing required 'n'" in schema_errors(schema, {})[0]
    assert "expected integer" in schema_errors(schema, {"n": "x"})[0]


@pytest.mark.unit
def test_bool_is_not_an_integer():
    assert not validate({"type": "integer"}, True)


@pytest.mark.unit
def test_empty_schema_accepts_anything():
    assert validate({}, {"whatever": 1})


@pytest.mark.unit
def test_domain_packages_reexport():
    from dvah.prompts import PromptStack, load_prompts  # noqa: F401
    from dvah.resources import Resource, load_resources  # noqa: F401
    from dvah.workflows import Workflow, load_workflows  # noqa: F401

    assert Resource(id="r1").id == "r1"
