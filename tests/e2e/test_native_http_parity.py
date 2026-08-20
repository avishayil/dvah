"""HttpToolProvider must produce the same ToolResult as NativeToolProvider.

If these diverge, a lab could pass in-process but behave differently over HTTP —
defeating the point of a transport-agnostic security boundary.
"""

import pytest

from dvah.models.operation import Operation
from dvah.providers.http_tools import HttpToolProvider
from dvah.providers.native_tools import NativeToolProvider
from dvah.services.world_state import FileStore, GithubStore

pytestmark = pytest.mark.e2e

_FILES_SEED = {"/a.txt": "hello", "/b.txt": "world"}
_GH_SEED = {"repo/x/y": {"issues": [{"id": 1, "title": "t"}]}}

_CASES = [
    Operation(namespace="files", action="read", resource="/a.txt"),
    Operation(namespace="files", action="read", resource="/missing"),
    Operation(namespace="files", action="delete", resource="/b.txt"),
    Operation(namespace="files", action="rename", resource="/a.txt", parameters={"dest": "/z.txt"}),
    Operation(namespace="github", action="issue.read", resource="repo/x/y"),
    Operation(namespace="github", action="issue.comment", resource="repo/x/y",
              parameters={"issue": 1, "body": "hi"}),
    Operation(namespace="github", action="repository.delete", resource="repo/x/y"),
]


@pytest.mark.parametrize("op", _CASES, ids=lambda o: f"{o.namespace}.{o.action}")
def test_native_and_http_agree(op, services, reset_services):
    reset_services({"files": {"files": dict(_FILES_SEED)}, "github": {"github": dict(_GH_SEED)}})
    native = NativeToolProvider(
        files=FileStore(seed=dict(_FILES_SEED)), github=GithubStore(seed=dict(_GH_SEED))
    )
    http = HttpToolProvider(base_urls=services)

    native_result = native.invoke(op)
    http_result = http.invoke(op)
    assert http_result.ok == native_result.ok
    assert http_result.output == native_result.output
    assert http_result.trust == native_result.trust
    assert http_result.source == native_result.source
