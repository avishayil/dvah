import pytest
from pydantic import ValidationError

from dvah.models.approval import ApprovalGrant
from dvah.models.runtime import Constraints, MCPServerRef, RuntimeContext, SkillRef

pytestmark = pytest.mark.unit


def test_constraints_defaults():
    c = Constraints()
    assert c.network_profile == "restricted"
    assert c.delegation_depth == 2
    assert c.max_actions == 20


def test_runtime_context_optional_refs():
    rc = RuntimeContext(model="m", skill=SkillRef(name="s", digest="d"),
                        mcp_server=MCPServerRef(name="mcp", digest="d2"))
    assert rc.skill.name == "s"
    assert rc.mcp_server.name == "mcp"


def test_approval_grant_frozen():
    g = ApprovalGrant(approval_id="a", approved_action_hash="sha256:x")
    with pytest.raises(ValidationError):
        g.approval_id = "b"
