"""Targeted coverage for small core modules (stores, scheduler, catalog, parsers)."""

import pytest

from dvah.artifacts.resource_yaml import load_resources
from dvah.artifacts.workflow_yaml import load_workflows
from dvah.guardrails.revocation import RevocationRegistry
from dvah.harness.scheduler import InterleavingScheduler, SequentialScheduler
from dvah.memory.store import BuiltinMemoryProvider, MemoryStore
from dvah.models.provenance import TrustLevel
from dvah.schemas.validators import schema_errors
from dvah.scenarios import catalog
from dvah.services.world_state import FileStore, GithubStore


@pytest.mark.unit
def test_file_store_delete_rename_reset():
    fs = FileStore(seed={"/a": "x"})
    assert fs.exists("/a") and fs.read("/a") == "x"
    assert fs.delete("/a") is True and fs.delete("/a") is False
    fs.reset(seed={"/b": "y"})
    assert fs.rename("/b", "/c") is True and fs.read("/c") == "y"
    assert fs.rename("/missing", "/z") is False


@pytest.mark.unit
def test_github_store_reset_and_exists():
    gh = GithubStore(seed={"acme/app": {"issues": [], "exists": True}})
    assert gh.exists("acme/app")
    gh.reset(seed={})
    assert not gh.exists("acme/app")


@pytest.mark.unit
def test_memory_store_add_notes_reset_recall():
    ms = MemoryStore(seed={"acme": [{"source": "s", "content": {"t": 1}}]})
    ms.add("acme", "s2", {"t": 2})
    assert len(ms.notes("acme")) == 2
    ms.reset(seed={})
    assert ms.notes("acme") == []
    ms.add("acme", "s", {"body": "hi"})
    recalled = BuiltinMemoryProvider(store=ms).recall("acme", "2026-01-01T00:00:00Z")
    assert recalled and recalled[0]["trust"] == TrustLevel.MEMORY


@pytest.mark.unit
def test_schedulers_run_in_order():
    seen = []
    SequentialScheduler().run([lambda: seen.append(0), lambda: seen.append(1)])
    assert seen == [0, 1]
    seen.clear()
    InterleavingScheduler(order=[1, 0, 1]).run([lambda: seen.append("a"), lambda: seen.append("b")])
    assert seen == ["b", "a", "b"]


@pytest.mark.unit
def test_revocation_registry(make_envelope):
    reg = RevocationRegistry()
    reg.revoke_action("files", "delete")
    reg.revoke_principal("mallory")
    from dvah.models.operation import Operation
    del_env = make_envelope(operation=Operation(namespace="files", action="delete", resource="/x"))
    read_env = make_envelope(operation=Operation(namespace="files", action="read", resource="/x"))
    assert reg.is_revoked(del_env) is True      # action revoked
    assert reg.is_revoked(read_env) is False


@pytest.mark.unit
def test_schema_errors_array_items():
    schema = {"type": "array", "items": {"type": "integer"}}
    assert schema_errors(schema, [1, 2]) == []
    errs = schema_errors(schema, [1, "x"])
    assert errs and "[1]" in errs[0]


@pytest.mark.unit
def test_catalog_escape_and_unknown(tmp_path):
    with pytest.raises(LookupError):
        catalog.resolve_challenge(str(tmp_path))  # exists but outside challenges/
    with pytest.raises(LookupError):
        catalog.resolve_challenge("DVAH-999")
    assert catalog.validate_challenge_id("DVAH-001") == "DVAH-001"
    with pytest.raises(LookupError):
        catalog.validate_challenge_id("../etc")


@pytest.mark.unit
def test_resource_yaml_new_format_and_errors(tmp_path):
    d = tmp_path / "lab"
    (d / "resources").mkdir(parents=True)
    (d / "resources" / "resources.yaml").write_text(
        "- {id: 'doc://policy', name: policy, content: 'be safe'}\n"
    )
    res = load_resources(d)
    assert res["doc://policy"].content == "be safe"

    (d / "resources" / "resources.yaml").write_text("id: notalist\n")
    with pytest.raises(ValueError, match="YAML list"):
        load_resources(d)
    (d / "resources" / "resources.yaml").write_text("- {name: no_id}\n")
    with pytest.raises(ValueError, match="needs an 'id'"):
        load_resources(d)


@pytest.mark.unit
def test_load_resources_empty_when_none(tmp_path):
    assert load_resources(tmp_path) == {}


@pytest.mark.unit
def test_load_workflows_empty_and_reflect_kind(tmp_path):
    assert load_workflows(tmp_path) == {}
    d = tmp_path / "lab"
    (d / "workflows").mkdir(parents=True)
    (d / "workflows" / "plans.yaml").write_text(
        "t1:\n  - {namespace: agent, action: reflect}\n  - {namespace: files, action: read, resource: /x}\n"
    )
    wfs = load_workflows(d)
    from dvah.models.workflow import StepKind
    assert wfs["t1"].steps[0].kind == StepKind.MODEL      # agent.reflect -> MODEL
    assert wfs["t1"].steps[1].kind == StepKind.TOOL
