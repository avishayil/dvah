"""Unit tests for the evolved runtime Skill model (v0.3 Phase 3)."""

import pytest

from dvah.models.capability import Capability
from dvah.models.skill import SkillManifest

pytestmark = pytest.mark.unit


def test_backcompat_construction():
    """The legacy shape SkillManifest(name, digest, permissions) still works."""
    m = SkillManifest(name="s", digest="v1", permissions=(Capability(namespace="github", action="issue.read"),))
    assert m.name == "s"
    assert m.version == ""
    assert m.instructions == ""
    assert m.tools == ()
    assert m.mcp == () and m.network == () and m.secrets == ()


def test_runtime_fields_and_requested_alias():
    m = SkillManifest(
        name="github-investigator",
        digest="v1.3",
        version="1.3.0",
        instructions="Investigate incidents using GitHub data.",
        tools=("github.issue.read", "github.issue.comment"),
        permissions=(Capability(namespace="github", action="issue.comment"),),
        mcp=("github",),
        network=("github-mcp",),
        secrets=("github-token",),
    )
    assert m.version == "1.3.0"
    assert "github.issue.comment" in m.tools
    # requesting is exposed as an alias — requesting is not granting.
    assert m.requested_permissions == m.permissions


def test_frozen():
    m = SkillManifest(name="s", digest="v1")
    with pytest.raises(Exception):
        m.name = "other"  # type: ignore[misc]
