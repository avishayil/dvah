import pytest

from dvah.artifacts.skill_md import load_skill
from dvah.models.capability import Capability

SKILL = """---
name: github-investigator
description: Triage incidents from GitHub issues.
version: 1.3.0
digest: v1.3
allowed-tools: [github.issue.read, github.issue.comment]
requested-permissions:
  - {namespace: github, action: issue.read}
  - {namespace: github, action: issue.comment}
network: [github-mcp]
secrets: [github-token]
---
Investigate incidents using GitHub data.
"""


@pytest.mark.unit
def test_skill_md_maps_all_frontmatter_fields(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text(SKILL)

    manifest = load_skill(path)

    assert manifest.name == "github-investigator"
    assert manifest.description == "Triage incidents from GitHub issues."
    assert manifest.version == "1.3.0"
    assert manifest.digest == "v1.3"
    assert manifest.tools == ("github.issue.read", "github.issue.comment")
    assert manifest.permissions == (
        Capability(namespace="github", action="issue.read"),
        Capability(namespace="github", action="issue.comment"),
    )
    assert manifest.network == ("github-mcp",)
    assert manifest.secrets == ("github-token",)
    assert manifest.instructions == "Investigate incidents using GitHub data."


@pytest.mark.unit
def test_allowed_tools_accepts_comma_string(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: s\ndigest: d\nallowed-tools: a.b, c.d\n---\nbody")
    manifest = load_skill(path)
    assert manifest.tools == ("a.b", "c.d")


@pytest.mark.unit
def test_missing_name_raises_with_path(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text("---\ndigest: d\n---\nbody")
    with pytest.raises(ValueError, match=str(path)):
        load_skill(path)


@pytest.mark.unit
def test_malformed_frontmatter_raises_with_path(tmp_path):
    path = tmp_path / "SKILL.md"
    path.write_text("---\nname: x\nno closing fence")
    with pytest.raises(ValueError, match=str(path)):
        load_skill(path)
