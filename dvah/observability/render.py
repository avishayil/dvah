"""Rendering for the security trace.

``summarize_trace`` is pure and unit-testable; ``render_trace`` turns a log into a rich
tree for ``dvah trace``, colouring denials, flagging executions that never received
execution-time authorization (INV-01), and surfacing untrusted-instruction leaks
(INV-06).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from rich.console import Console
from rich.tree import Tree

from .trace import TraceLog

# Per-event-kind glyph + colour for the tree.
_STYLE = {
    "envelope.built": ("•", "dim"),
    "policy.decision": ("⚖", "white"),
    "approval.used": ("🔑", "cyan"),
    "delegate": ("→", "magenta"),
    "context.compiled": ("∑", "blue"),
    "provenance.recorded": ("◆", "dim"),
    "executed": ("✓", "green"),
    "denied": ("✗", "red bold"),
}
_VERDICT_COLOUR = {"allow": "green", "deny": "red", "needs_approval": "yellow"}


class TraceSummary(BaseModel):
    """A pure, testable digest of a run's security trace."""

    model_config = ConfigDict(frozen=True)

    total_events: int
    executed: int
    denials: tuple[dict, ...] = ()
    unauthorized_executions: tuple[str, ...] = ()
    delegations: tuple[str, ...] = ()
    untrusted_instruction: bool = False

    @property
    def clean(self) -> bool:
        return not self.unauthorized_executions and not self.untrusted_instruction


def summarize_trace(trace: TraceLog) -> TraceSummary:
    denials = tuple(
        {"action_hash": e.action_hash, "invariant": e.detail.get("invariant")}
        for e in trace.of_kind("denied")
    )
    delegations = tuple(
        str(e.detail.get("child")) for e in trace.of_kind("delegate")
    )
    untrusted = any(
        e.detail.get("untrusted_instruction") for e in trace.of_kind("context.compiled")
    )
    return TraceSummary(
        total_events=len(trace.events),
        executed=len(trace.executed_hashes()),
        denials=denials,
        unauthorized_executions=tuple(trace.unauthorized_executions()),
        delegations=delegations,
        untrusted_instruction=untrusted,
    )


def _short(action_hash: str | None) -> str:
    if not action_hash:
        return "-"
    return action_hash.replace("sha256:", "")[:10]


def _event_label(event) -> str:
    glyph, colour = _STYLE.get(event.kind, ("·", "white"))
    d = event.detail
    if event.kind == "policy.decision":
        verdict = d.get("verdict", "?")
        colour = _VERDICT_COLOUR.get(verdict, "white")
        extra = f"{verdict}" + (f" [{d['invariant']}]" if d.get("invariant") else "")
        extra += f" — {d.get('reason', '')}"
    elif event.kind in {"envelope.built", "executed"}:
        extra = f"{d.get('namespace', '?')}.{d.get('action', '?')}"
        if d.get("resource"):
            extra += f" {d['resource']}"
    elif event.kind == "delegate":
        extra = f"{d.get('child')} caps={d.get('child_caps')}"
    elif event.kind == "context.compiled":
        leak = d.get("untrusted_instruction")
        extra = "[red]UNTRUSTED DATA IN INSTRUCTION CHANNEL[/red]" if leak else "clean"
    elif event.kind == "provenance.recorded":
        extra = f"sources={d.get('sources')}"
    elif event.kind == "denied":
        extra = f"[red]{d.get('invariant', '')}[/red]"
    else:
        extra = str(d) if d else ""
    return f"[{colour}]{glyph} {event.kind:18}[/{colour}] [dim]{_short(event.action_hash)}[/dim] {extra}"


def render_trace(trace: TraceLog, console: Console) -> None:
    events = trace.events
    task_id = events[0].task_id if events else "?"
    tree = Tree(f"[bold]task[/bold] {task_id}")
    for event in events:
        tree.add(_event_label(event))
    console.print(tree)

    summary = summarize_trace(trace)
    console.print(
        f"\n[bold]{summary.executed} executed[/bold], "
        f"{len(summary.denials)} denied, "
        f"{len(summary.delegations)} delegation(s)"
    )
    for h in summary.unauthorized_executions:
        console.print(
            f"[red bold]⚠ INV-01:[/red bold] executed [dim]{_short(h)}[/dim] "
            "without execution-time authorization (authorization used tool/plan "
            "identity rather than the resolved operation)."
        )
    if summary.untrusted_instruction:
        console.print(
            "[red bold]⚠ INV-06:[/red bold] untrusted data reached the instruction "
            "channel — retrieved content can be executed as instructions."
        )
    if summary.clean and not summary.denials:
        console.print("[green]no invariant violations observed in this trace.[/green]")
