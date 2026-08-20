"""DVAH command-line interface.

    dvah test  <challenge> [--adversarial]   run a lab's functional/exploit/invariant suite
    dvah trace <challenge> <task_id>         run a task and render its security trace
    dvah start <challenge>                   print the lab briefing (learn mode)
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(add_completion=False, help="Damn Vulnerable Agent Harness")
console = Console()

from .scenarios import catalog

CHALLENGES_DIR = catalog.CHALLENGES_DIR


def _resolve_challenge(challenge: str) -> Path:
    try:
        return catalog.resolve_challenge(challenge)
    except LookupError as exc:
        raise typer.BadParameter(str(exc)) from exc


def _read_scenario(challenge_dir: Path) -> dict:
    return catalog.read_scenario(challenge_dir)


def _iter_scenarios():
    return catalog.iter_scenarios()


def _print_learn_briefing(challenge_dir: Path, spec: dict) -> None:
    from rich.markdown import Markdown

    readme = challenge_dir / "README.md"
    if readme.exists():
        console.print(Markdown(readme.read_text()))
    else:
        console.print(f"[bold]{spec['id']}[/bold] — {spec.get('title', '')}")
    console.print(
        "\n[dim]docs/INVARIANTS.md and docs/ARCHITECTURE.md explain the invariants and "
        "the harness/security split.[/dim]"
    )


def _print_ctf_briefing(challenge_dir: Path, spec: dict) -> None:
    """Minimal briefing: objective + environment + where the source lives. No hints."""
    console.print(f"[bold cyan]{spec['id']}[/bold cyan] — {spec.get('title', '')}")
    console.print(f"difficulty: {spec.get('difficulty', '?')}")
    objective = (spec.get("objective") or {}).get("exploit", "")
    if objective:
        console.print(f"\n[bold]objective[/bold]\n{objective.strip()}")
    console.print("\n[bold]environment[/bold]")
    for name in ("users", "agents", "resources"):
        path = challenge_dir / "environment" / f"{name}.yaml"
        if path.exists():
            console.print(f"  {path.relative_to(challenge_dir)}")
    editable = sorted((challenge_dir / "guardrails" / "vulnerable").glob("*.py"))
    console.print("\n[bold]source to patch[/bold] (edit in place)")
    for f in editable:
        if f.name != "__init__.py":
            console.print(f"  vulnerable/{f.name}")
    console.print("\n[dim]No hints in ctf mode. Prove your fix with:[/dim] "
                  f"dvah test {spec['id']} --adversarial")


@app.command()
def test(challenge: str, adversarial: bool = typer.Option(False, "--adversarial")) -> None:
    """Run a challenge's test suite and report which invariants hold."""
    import pytest

    challenge_dir = _resolve_challenge(challenge)
    markers = "functional or exploit or invariant"
    if adversarial:
        markers += " or adversarial"
    code = pytest.main(
        ["-q", str(challenge_dir / "evals"), "-m", markers, f"--challenge={challenge_dir}"]
    )
    raise typer.Exit(code)


@app.command()
def trace(
    challenge: str,
    task_id: str,
    solution: bool = typer.Option(False, "--solution", help="trace the reference fix"),
) -> None:
    """Run a task and render its security trace as an annotated tree."""
    from .observability.render import render_trace
    from .scenarios.loader import load_challenge

    loaded = load_challenge(_resolve_challenge(challenge), use_solution=solution)
    try:
        loaded.harness.run_task(loaded.root_ctx, task_id)
    except Exception as exc:  # a denial legitimately terminates the trace
        console.print(f"[yellow]task halted:[/yellow] {exc}\n")
    render_trace(loaded.trace, console)


@app.command("list")
def list_challenges() -> None:
    """List the available challenges."""
    from rich.table import Table

    table = Table(title="DVAH challenges")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Invariants", style="magenta")
    for spec in _iter_scenarios():
        table.add_row(spec["id"], spec.get("title", ""), ", ".join(spec.get("invariants", [])))
    console.print(table)


@app.command()
def start(
    challenge: str,
    mode: str = typer.Option("learn", help="learn (full briefing) or ctf (objective only)"),
) -> None:
    """Print the lab briefing. ``--mode learn`` shows hints; ``--mode ctf`` shows only the objective + environment."""
    challenge_dir = _resolve_challenge(challenge)
    spec = _read_scenario(challenge_dir)
    if mode == "ctf":
        _print_ctf_briefing(challenge_dir, spec)
    else:
        _print_learn_briefing(challenge_dir, spec)


@app.command()
def mutate(
    seed: int = typer.Option(0, help="deterministic seed selecting hidden defeats"),
    count: int = typer.Option(2, help="how many invariant defeats to toggle"),
    reveal: bool = typer.Option(False, "--reveal/--no-reveal", help="disclose the toggled defeats"),
) -> None:
    """Toggle a hidden subset of invariant defeats and report which invariants hold."""
    from .mutation.engine import choose_flags, run

    flags = choose_flags(seed, count)
    result = run(flags)
    console.print("[bold]DVAH MUTATION ENGINE[/bold]")
    console.print(f"seed={seed} count={count}\n")
    console.print("Security invariants")
    for inv, ok in result.holds.items():
        mark = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  {mark} {inv}")
    console.print(f"\nResult: {result.holding} / {result.total} invariants hold")
    if reveal:
        active = ", ".join(flags.active()) or "(none)"
        console.print(f"\n[yellow]revealed defeats:[/yellow] {active}")
    raise typer.Exit(0 if result.holding == result.total else 1)


def _grader_observed_line() -> str:
    """Live grader-observed INV-01: DVAH performs a real side effect through its own
    mock services and reconciles what they RECORDED against the claim. Requires the
    services (``docker compose --profile services up``); skipped if unreachable."""
    from .conformance.observed import observed_side_effects, read_recorder, reconcile, reset_service
    from .providers.http_tools import DEFAULT_BASE_URLS, HttpToolProvider
    from .models.operation import Operation

    files = DEFAULT_BASE_URLS["files"]
    try:
        reset_service(files, {"files": {"/tmp/a": "data"}})
    except Exception:
        return "[yellow]grader-observed:[/yellow] services not reachable — skipped " \
               "(start them with `docker compose --profile services up`)"
    HttpToolProvider().invoke(Operation(namespace="files", action="delete",
                                        resource="/tmp/a", parameters={}))
    observed = observed_side_effects(read_recorder(files))
    res = reconcile([("files", "delete", "/tmp/a")], observed)
    mark = "[green]✓[/green]" if res.holds else "[red]✗[/red]"
    return f"  {mark} {res.invariant:14} {res.detail}"


@app.command()
def conformance(
    adapter: str = typer.Option("builtin", help="which harness adapter to grade: builtin | external"),
    json_out: bool = typer.Option(False, "--json", help="emit machine-readable JSON"),
    observed: bool = typer.Option(False, "--observed",
                                  help="also run live grader-observed INV-01 against the mock services"),
) -> None:
    """Grade a harness adapter against the invariant conformance battery (INV-01..14)."""
    from .conformance import BuiltinAdapter, ExternalHarness, run_battery

    adapters = {"builtin": BuiltinAdapter, "external": ExternalHarness}
    if adapter not in adapters:
        raise typer.BadParameter(f"unknown adapter {adapter!r}; choose builtin|external")
    run = run_battery(adapters[adapter]())
    if json_out:
        console.print_json(data={
            "adapter": run.adapter,
            "holding": run.holding,
            "total": run.total,
            "results": [
                {"invariant": r.invariant, "holds": r.holds, "detail": r.detail}
                for r in run.results
            ],
        })
    else:
        console.print(f"[bold]DVAH CONFORMANCE[/bold] — adapter: {run.adapter}\n")
        for r in run.results:
            mark = "[green]✓[/green]" if r.holds else "[red]✗[/red]"
            console.print(f"  {mark} {r.invariant:14} {r.detail}")
        console.print(f"\nResult: {run.holding} / {run.total} invariants hold")
        if observed:
            console.print("\n[bold]grader-observed[/bold] (grounded in DVAH-controlled services):")
            console.print(_grader_observed_line())
    raise typer.Exit(0 if run.passed else 1)


@app.command()
def run(
    challenge: str,
    task_id: str,
    model: str = typer.Option("deterministic", help="deterministic (default/CI oracle) | a provider/profile e.g. anthropic|openai|bedrock|balanced|smart"),
    record: str = typer.Option("", "--record", help="write the session (turns + trace + verdict) to this JSON file"),
    solution: bool = typer.Option(False, "--solution", help="run the reference fix"),
) -> None:
    """Run a task through the agent loop and show the trace + the two scores.

    ``--model deterministic`` replays the scripted plan (CI oracle). Any other selection
    resolves through model profiles to a live model, with the deterministic session as a
    safe fallback if no key/SDK is configured — so this never crashes when unconfigured.
    """
    import os

    from .observability.render import render_trace
    from .providers.model import AgentState
    from .providers.router_model import build_model_session
    from .replay import run_and_record
    from .scenarios.loader import load_challenge
    from .scoring import as_dict, dual_score

    challenge_dir = _resolve_challenge(challenge)
    spec = _read_scenario(challenge_dir)
    loaded = load_challenge(challenge_dir, use_solution=solution)
    session = build_model_session(
        model,
        deterministic_provider=loaded.harness.cfg.model,
        task_id=task_id,
        prompt=loaded.task_prompt(task_id),
        trace=loaded.trace,
        env=dict(os.environ),
    )
    if record:
        run_and_record(loaded, spec["id"], task_id, session, record)
    else:
        try:
            loaded.harness.run_session(
                loaded.root_ctx, session, AgentState(task_id=task_id),
                prompt=loaded.task_prompt(task_id),
            )
        except Exception as exc:  # a denial legitimately halts the run
            console.print(f"[yellow]task halted:[/yellow] {exc}\n")
    render_trace(loaded.trace, console)
    score = as_dict(dual_score(loaded.trace))
    sec, ex = score["runtime_security"], score["live_agent_exercise"]
    console.print("\n[bold]Runtime Security[/bold] (deterministic, model-independent)")
    mark = "[green]✓ secure[/green]" if sec["secure"] else "[red]✗ vulnerable[/red]"
    console.print(f"  {mark} — {sec['basis']}")
    console.print("[bold]Live Agent Exercise[/bold] (what the model did this run)")
    console.print(f"  {ex['summary']}")
    if ex["avoided"]:
        console.print("  [dim]the model avoided the bait — this does NOT prove the harness is "
                      f"secure. Verify: dvah run {spec['id']} {task_id} (deterministic).[/dim]")
    if record:
        console.print(f"\n[dim]recorded to {record} — replay with: dvah replay {record}[/dim]")


@app.command("replay")
def replay_cmd(
    recording: str,
    solution: bool = typer.Option(False, "--solution", help="replay against the reference fix"),
) -> None:
    """Replay a recorded session with NO model calls and confirm the security verdict reproduces."""
    from .replay import replay as _replay

    res = _replay(recording, use_solution=solution)
    console.print(f"[bold]replay[/bold] {res['challenge_id']} :: {res['task_id']}")
    console.print(f"  recorded verdict:   {res['recorded']}")
    console.print(f"  reproduced verdict: {res['reproduced']}")
    mark = "[green]✓ matches[/green]" if res["matches"] else "[red]✗ diverged[/red]"
    console.print(f"  {mark} (no model calls)")
    raise typer.Exit(0 if res["matches"] else 1)


if __name__ == "__main__":
    app()
