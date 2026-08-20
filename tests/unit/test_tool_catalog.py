import pytest

from dvah.artifacts.tool_catalog import builtin_catalog, load_catalog_file, overlay
from dvah.models.tool_spec import ToolSpec

# The concrete namespace.action set the native + HTTP providers implement.
PROVIDER_ACTIONS = {
    "files.read", "files.delete", "files.rename",
    "github.issue.read", "github.issue.comment", "github.repository.delete",
    "email.send", "cloud.instance.list", "cloud.instance.terminate",
    "mcp.fetch",
}


@pytest.mark.unit
def test_builtin_catalog_covers_every_provider_action():
    catalog = builtin_catalog()
    assert set(catalog) == PROVIDER_ACTIONS
    spec = catalog["github.issue.comment"]
    assert isinstance(spec, ToolSpec)
    assert spec.id == "github.issue.comment"
    assert spec.input_schema["type"] == "object"
    assert "body" in spec.input_schema["properties"]


@pytest.mark.unit
def test_load_catalog_file_rejects_non_list(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("namespace: files\naction: read\n")
    with pytest.raises(ValueError, match="must be a YAML list"):
        load_catalog_file(path)


@pytest.mark.unit
def test_load_catalog_file_requires_namespace_and_action(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("- name: no_ns\n")
    with pytest.raises(ValueError, match="needs 'namespace' and 'action'"):
        load_catalog_file(path)


@pytest.mark.unit
def test_overlay_is_immutable_and_overrides():
    base = {"files.read": ToolSpec(namespace="files", action="read", name="orig")}
    extra = {"files.read": ToolSpec(namespace="files", action="read", name="new")}
    merged = overlay(base, extra)
    assert merged["files.read"].name == "new"
    assert base["files.read"].name == "orig"  # unchanged
