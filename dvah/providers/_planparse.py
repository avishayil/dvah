"""Shared helpers for LLM-backed model adapters.

All adapters turn a task into a JSON plan and parse it into ``PlanStep``s. The parsing
is model-agnostic: the model only proposes steps, which carry no authority until the
runtime resolves and authorizes them.
"""

from __future__ import annotations

import json

from .model import ModelRequest, PlanStep

#: System instruction shared by every LLM adapter.
SYSTEM_PROMPT = (
    "You are a planning component inside a security-hardened agent runtime. "
    "Given a task, respond with ONLY a JSON object of the form "
    '{"plan": [{"namespace": str, "action": str, "resource": str, "parameters": {}}]}. '
    "Each step is a proposal; it carries no authority until the runtime authorizes it. "
    "Do not include prose, code fences, or explanation — JSON only."
)


def render_prompt(request: ModelRequest) -> str:
    """Serialize the request (prompt + trust-labeled context) as a JSON user message."""
    return json.dumps(
        {
            "task_id": request.task_id,
            "prompt": request.prompt,
            "context": list(request.context),
        }
    )


def strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```", 2)[1]
        if stripped.startswith("json"):
            stripped = stripped[len("json"):]
    return stripped.strip()


def parse_steps(text: str) -> tuple[PlanStep, ...]:
    """Parse model output (``{"plan":[...]}`` or a bare ``[...]``) into PlanSteps."""
    data = json.loads(strip_fences(text))
    steps = data.get("plan", data) if isinstance(data, dict) else data
    if not isinstance(steps, list):
        raise ValueError("model did not return a plan list")
    return tuple(PlanStep(**step) for step in steps)
