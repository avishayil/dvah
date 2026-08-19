import pytest

from dvah.models.hashing import canonical_json, sha256_of

pytestmark = pytest.mark.unit


def test_canonical_json_is_key_order_independent():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_canonical_json_has_no_incidental_whitespace():
    assert canonical_json({"a": 1, "b": 2}) == '{"a":1,"b":2}'


def test_canonical_json_falls_back_to_str_for_unknown_types():
    class Thing:
        def __str__(self):
            return "thing"

    assert canonical_json({"x": Thing()}) == '{"x":"thing"}'


def test_sha256_of_is_prefixed_and_stable():
    digest = sha256_of({"a": 1})
    assert digest.startswith("sha256:")
    assert digest == sha256_of({"a": 1})


def test_sha256_of_differs_for_different_content():
    assert sha256_of({"a": 1}) != sha256_of({"a": 2})
