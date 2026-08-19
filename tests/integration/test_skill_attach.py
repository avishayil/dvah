"""Integration tests for skill attach in the agent loop (v0.3 Phase 3, INV-07).

A skill *requests* capabilities; attaching it must never *grant* beyond the approved set.
The correct loader (DVAH-009 solution) grants requested ∩ approved and flags the rest for
re-approval; the vulnerable loader silently widens.
"""

from pathlib import Path

import pytest

from dvah.models.capability import Capability, CapabilitySet
from dvah.models.skill import SkillManifest
from dvah.scenarios.loader import load_challenge

pytestmark = pytest.mark.integration

CHALLENGES = Path(__file__).resolve().parents[2] / "challenges"
DVAH_009 = CHALLENGES / "DVAH-009-skill-upgrade"

READ = Capability(namespace="github", action="issue.read")
COMMENT = Capability(namespace="github", action="issue.comment")
APPROVED = (READ,)  # what v1.2 was approved for
UPGRADE = SkillManifest(  # v1.3 quietly requests issue.comment on top
    name="github-investigator",
    digest="v1.3",
    version="1.3.0",
    instructions="Investigate incidents using GitHub data.",
    tools=("github.issue.read", "github.issue.comment"),
    permissions=(READ, COMMENT),
)


def _granted_actions(res):
    return {(c.namespace, c.action) for c in res.granted.caps}


def test_solution_loader_does_not_grant_beyond_approved():
    """INV-07: requesting ≠ granting. The fixed loader keeps granted ⊆ approved and flags
    the expansion for re-approval, so the skill is NOT attached."""
    loaded = load_challenge(DVAH_009, use_solution=True)
    ctx, res = loaded.harness.attach_skill(loaded.root_ctx, UPGRADE, APPROVED, pinned_digest=None)

    assert _granted_actions(res) == {("github", "issue.read")}  # comment NOT granted
    assert res.requires_reapproval is True
    assert ("github", "issue.comment") in {(c.namespace, c.action) for c in res.expanded}
    assert ctx.skills == ()  # not attached — needs re-approval

    ev = loaded.harness.cfg.trace.of_kind("skill.loaded")
    assert ev and ev[-1].detail["requires_reapproval"] is True


def test_vulnerable_loader_silently_widens():
    """The vulnerable loader grants everything the upgraded manifest requests — the
    silent capability expansion INV-07 exists to catch."""
    loaded = load_challenge(DVAH_009, use_solution=False)
    _ctx, res = loaded.harness.attach_skill(loaded.root_ctx, UPGRADE, APPROVED, pinned_digest=None)

    assert ("github", "issue.comment") in _granted_actions(res)  # widened beyond approved
    assert res.requires_reapproval is False


def test_trusted_nonexpanding_skill_is_attached_and_injected():
    """A trusted skill whose request is within the approved set attaches and contributes
    its instruction fragment to the compiled context (on the trusted INSTRUCTION channel,
    so INV-06 is not tripped)."""
    loaded = load_challenge(DVAH_009, use_solution=True)
    skill = SkillManifest(
        name="github-reader",
        digest="v1.2",
        version="1.2.0",
        instructions="Read GitHub issues to triage incidents.",
        tools=("github.issue.read",),
        permissions=(READ,),
    )
    ctx, res = loaded.harness.attach_skill(ctx=loaded.root_ctx, skill=skill, approved_permissions=APPROVED)
    assert res.requires_reapproval is False
    assert ctx.skills and ctx.skills[0].name == "github-reader"

    compiled = loaded.harness.cfg.context_compiler.compile(ctx)
    sources = [i.source for i in compiled.items]
    assert "skill:github-reader" in sources
    # the injected skill instruction must not read as untrusted (INV-06 stays clean)
    assert compiled.has_untrusted_instruction() is False
