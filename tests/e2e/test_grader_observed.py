"""Grader-observed conformance against LIVE DVAH-controlled services (e2e-only).

Drives a real side effect through the mock services, reads their authoritative
``/_recorder``, and shows the reconcile passes for an honest claim and catches a
lying one. Marked e2e (excluded from CI) — needs the uvicorn services fixture.
"""

import pytest

from dvah.conformance.observed import observed_side_effects, read_recorder, reconcile
from dvah.models.operation import Operation
from dvah.providers.http_tools import HttpToolProvider

pytestmark = pytest.mark.e2e


def test_grader_observes_real_side_effects(services, reset_services):
    reset_services({"files": {"files": {"/tmp/a": "data"}}})
    provider = HttpToolProvider(base_urls=services)

    result = provider.invoke(
        Operation(namespace="files", action="delete", resource="/tmp/a", parameters={})
    )
    assert result.ok

    observed = observed_side_effects(read_recorder(services["files"]))
    assert observed == [("files", "delete", "/tmp/a")]

    # Honest adapter: what it claims matches what DVAH recorded.
    assert reconcile([("files", "delete", "/tmp/a")], observed).holds

    # Lying adapter: claims a repo delete the services never performed → caught.
    liar = [("files", "delete", "/tmp/a"), ("github", "repository.delete", "repo/x")]
    assert not reconcile(liar, observed).holds
