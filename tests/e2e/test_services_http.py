import httpx
import pytest

from dvah.models.operation import Operation
from dvah.providers.http_tools import HttpToolProvider

pytestmark = pytest.mark.e2e


@pytest.fixture
def provider(services):
    return HttpToolProvider(base_urls=services)


def test_files_read_delete_rename(provider, reset_services):
    reset_services({"files": {"files": {"/a.txt": "hello", "/b.txt": "keep"}}})
    read = provider.invoke(Operation(namespace="files", action="read", resource="/a.txt"))
    assert read.ok and read.output["contents"] == "hello"

    deleted = provider.invoke(Operation(namespace="files", action="delete", resource="/a.txt"))
    assert deleted.ok
    assert provider.invoke(Operation(namespace="files", action="read", resource="/a.txt")).ok is False

    renamed = provider.invoke(
        Operation(namespace="files", action="rename", resource="/b.txt", parameters={"dest": "/c.txt"})
    )
    assert renamed.ok
    assert provider.invoke(Operation(namespace="files", action="read", resource="/c.txt")).ok


def test_github_read_comment_delete(provider, reset_services):
    reset_services({"github": {"github": {"repo/x/y": {"issues": [{"id": 1, "title": "t"}]}}}})
    issues = provider.invoke(Operation(namespace="github", action="issue.read", resource="repo/x/y"))
    assert issues.ok and issues.output["issues"][0]["id"] == 1

    commented = provider.invoke(
        Operation(namespace="github", action="issue.comment", resource="repo/x/y",
                  parameters={"issue": 1, "body": "hi"})
    )
    assert commented.ok

    deleted = provider.invoke(Operation(namespace="github", action="repository.delete", resource="repo/x/y"))
    assert deleted.ok


def test_email_send_and_outbox(provider, reset_services, services):
    reset_services()
    sent = provider.invoke(
        Operation(namespace="email", action="send", resource="bob@example.com",
                  parameters={"to": "bob@example.com", "subject": "s", "body": "b"})
    )
    assert sent.ok and sent.output["id"] == 1
    outbox = httpx.get(f"{services['email']}/email/outbox", timeout=2.0).json()["outbox"]
    assert outbox[0]["to"] == "bob@example.com"


def test_cloud_list_and_terminate(provider, reset_services):
    reset_services({"cloud": {"cloud": {"i-123": {"name": "web"}}}})
    listed = provider.invoke(Operation(namespace="cloud", action="instance.list", resource="*"))
    assert listed.ok and listed.output["instances"][0]["id"] == "i-123"

    terminated = provider.invoke(Operation(namespace="cloud", action="instance.terminate", resource="i-123"))
    assert terminated.ok
    assert provider.invoke(Operation(namespace="cloud", action="instance.terminate", resource="i-123")).ok is False
