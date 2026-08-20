"""Schemas layer — validators for tool/agent OUTPUT schemas (JSON Schema, MCP-aligned).

Dependency-free structural validation (no jsonschema dep): enough to advisory-check that a
tool result or agent output conforms to its declared ``output_schema``. Never used for
authorization — purely a fidelity/eval aid.
"""

from .validators import schema_errors, validate

__all__ = ["schema_errors", "validate"]
