import pytest
from pydantic import ValidationError

from dvah.models.operation import Operation

pytestmark = pytest.mark.unit


def test_parameters_hash_is_stable_and_order_independent():
    a = Operation(namespace="email", action="send", resource="msg", parameters={"to": "b", "cc": "c"})
    b = Operation(namespace="email", action="send", resource="msg", parameters={"cc": "c", "to": "b"})
    assert a.parameters_hash == b.parameters_hash


def test_parameters_hash_changes_with_parameters():
    a = Operation(namespace="email", action="send", resource="msg", parameters={"to": "b"})
    a2 = a.with_parameters({"to": "everyone"})
    assert a.parameters_hash != a2.parameters_hash


def test_with_parameters_returns_new_copy():
    a = Operation(namespace="files", action="read", resource="/x")
    a2 = a.with_parameters({"k": "v"})
    assert a2.parameters == {"k": "v"}
    assert a.parameters == {}


def test_operation_is_frozen():
    op = Operation(namespace="files", action="read", resource="/x")
    with pytest.raises(ValidationError):
        op.resource = "/y"
