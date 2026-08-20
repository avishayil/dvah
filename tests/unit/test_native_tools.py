import pytest

from dvah.models.operation import Operation
from dvah.models.provenance import TrustLevel
from dvah.providers.native_tools import NativeToolProvider
from dvah.services.world_state import FileStore, GithubStore

pytestmark = pytest.mark.unit


@pytest.fixture
def provider():
    files = FileStore(seed={"/tmp/x": "data"})
    github = GithubStore(seed={"repo/a": {"issues": [{"id": 1}]}})
    return NativeToolProvider(files=files, github=github), files, github


def test_supports_known_namespaces(provider):
    p, _, _ = provider
    assert p.supports("files") and p.supports("github")
    assert not p.supports("email")


def test_files_read(provider):
    p, _, _ = provider
    result = p.invoke(Operation(namespace="files", action="read", resource="/tmp/x"))
    assert result.ok
    assert result.output["contents"] == "data"
    assert result.trust is TrustLevel.UNTRUSTED_DATA
    assert result.source == "files:/tmp/x"


def test_files_read_missing(provider):
    p, _, _ = provider
    result = p.invoke(Operation(namespace="files", action="read", resource="/nope"))
    assert not result.ok


def test_files_delete(provider):
    p, files, _ = provider
    assert p.invoke(Operation(namespace="files", action="delete", resource="/tmp/x")).ok
    assert not files.exists("/tmp/x")


def test_files_rename(provider):
    p, files, _ = provider
    result = p.invoke(Operation(namespace="files", action="rename", resource="/tmp/x",
                                parameters={"dest": "/tmp/y"}))
    assert result.ok
    assert files.exists("/tmp/y") and not files.exists("/tmp/x")


def test_files_unknown_action(provider):
    p, _, _ = provider
    assert not p.invoke(Operation(namespace="files", action="chmod", resource="/tmp/x")).ok


def test_github_issue_read(provider):
    p, _, _ = provider
    result = p.invoke(Operation(namespace="github", action="issue.read", resource="repo/a"))
    assert result.ok
    assert result.output["issues"][0]["id"] == 1


def test_github_comment(provider):
    p, _, _ = provider
    result = p.invoke(Operation(namespace="github", action="issue.comment", resource="repo/a",
                                parameters={"issue": 1, "body": "hi"}))
    assert result.ok


def test_github_repository_delete(provider):
    p, _, github = provider
    assert p.invoke(Operation(namespace="github", action="repository.delete", resource="repo/a")).ok
    assert not github.exists("repo/a")


def test_github_unknown_action(provider):
    p, _, _ = provider
    assert not p.invoke(Operation(namespace="github", action="fork", resource="repo/a")).ok


def test_unknown_namespace(provider):
    p, _, _ = provider
    assert not p.invoke(Operation(namespace="slack", action="post", resource="c")).ok
