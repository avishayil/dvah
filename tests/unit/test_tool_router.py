"""ToolRouter multiplexes providers by namespace and reports external-ness per-namespace.

The router must (a) dispatch to the first sub-provider that supports the namespace,
(b) error cleanly on an unsupported namespace, and (c) report ``is_external_for`` from the
sub-provider that would actually handle the op — the fact INV-14 depends on.
"""

from __future__ import annotations

import pytest

from dvah.models.operation import Operation
from dvah.providers.router import ToolRouter
from dvah.providers.tools import ToolResult

pytestmark = pytest.mark.unit


class _Provider:
    def __init__(self, namespaces, is_external, tag):
        self._ns = set(namespaces)
        self.is_external = is_external
        self._tag = tag

    def supports(self, namespace):
        return namespace in self._ns

    def invoke(self, operation, credential=None):
        return ToolResult(ok=True, output={"by": self._tag}, source=self._tag)


def _op(ns):
    return Operation(namespace=ns, action="read", resource="/x")


def test_dispatches_to_first_supporting_provider():
    native = _Provider({"files", "github"}, is_external=False, tag="native")
    mcp = _Provider({"mcp"}, is_external=True, tag="mcp")
    router = ToolRouter((native, mcp))

    assert router.invoke(_op("files")).output["by"] == "native"
    assert router.invoke(_op("mcp")).output["by"] == "mcp"


def test_first_match_wins_on_overlap():
    a = _Provider({"files"}, is_external=False, tag="a")
    b = _Provider({"files"}, is_external=True, tag="b")
    router = ToolRouter((a, b))
    assert router.invoke(_op("files")).output["by"] == "a"
    assert router.provider_for("files") is a


def test_unsupported_namespace_errors_cleanly():
    router = ToolRouter((_Provider({"files"}, is_external=False, tag="native"),))
    assert not router.supports("cloud")
    res = router.invoke(_op("cloud"))
    assert res.ok is False and "no tool provider" in res.output["error"]


def test_is_external_is_per_namespace():
    native = _Provider({"files", "github"}, is_external=False, tag="native")
    mcp = _Provider({"mcp"}, is_external=True, tag="mcp")
    router = ToolRouter((native, mcp))

    assert router.is_external_for("files") is False
    assert router.is_external_for("github") is False
    assert router.is_external_for("mcp") is True
    # Unknown namespace: treated as non-external (it errors on invoke anyway).
    assert router.is_external_for("cloud") is False
    # Flat fallback is the conservative OR for code that doesn't ask per-namespace.
    assert router.is_external is True
