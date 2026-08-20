"""Minimal, dependency-free JSON-Schema structural validation.

Supports the subset the tool/agent output schemas use: ``type`` (object/array/string/
integer/number/boolean/null), ``properties``, ``required``, and nested ``items``. Returns a
list of human-readable errors (empty = valid). Advisory only.
"""

from __future__ import annotations

_PY_TYPES = {
    "object": dict, "array": (list, tuple), "string": str,
    "integer": int, "number": (int, float), "boolean": bool, "null": type(None),
}


def schema_errors(schema: dict, data, _path: str = "$") -> list[str]:
    """Return structural mismatches between ``data`` and a JSON-Schema-ish ``schema``."""
    if not schema:
        return []
    errors: list[str] = []
    expected = schema.get("type")
    if expected:
        py = _PY_TYPES.get(expected)
        # bool is a subclass of int; guard so integers don't accept booleans.
        if py and (not isinstance(data, py) or (expected in ("integer", "number") and isinstance(data, bool))):
            errors.append(f"{_path}: expected {expected}, got {type(data).__name__}")
            return errors
    if expected == "object" and isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{_path}: missing required '{key}'")
        for key, subschema in (schema.get("properties") or {}).items():
            if key in data:
                errors.extend(schema_errors(subschema, data[key], f"{_path}.{key}"))
    elif expected == "array" and isinstance(data, (list, tuple)):
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                errors.extend(schema_errors(item_schema, item, f"{_path}[{i}]"))
    return errors


def validate(schema: dict, data) -> bool:
    return not schema_errors(schema, data)
