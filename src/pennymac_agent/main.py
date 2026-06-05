"""Command-line entry point for the PennyMac Trading Desktop Agent.

Usage:
    python -m pennymac_agent                 # interactive REPL
    python -m pennymac_agent run "..."       # one-shot request
    python -m pennymac_agent info            # show config + registered agents
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from .config.settings import get_settings
from .orchestrator.orchestrator import build_default_orchestrator, build_registry
from .utils.logging import get_logger

app = typer.Typer(
    add_completion=False,
    help="PennyMac Trading Desktop Agent - Orchestrator + Sub-Agents.",
)
console = Console()
logger = get_logger(__name__)


def _dry_run_notice(settings) -> None:
    console.print(
        Panel.fit(
            f"[yellow]Dry-run mode[/yellow]: LLM provider "
            f"'[bold]{settings.llm_provider}[/bold]' has no API key set.\n"
            "Set the key in .env to enable live orchestration. Showing the "
            "registered agents instead.",
            title="Not configured",
        )
    )
    registry = build_registry(settings)
    orch_caps = "\n".join(
        f"  - [bold]{s.name}[/bold]: {s.description}"
        for s in registry.tool_specs()
    )
    console.print(orch_caps)


def _run_once(request: str) -> None:
    settings = get_settings()
    if not settings.llm_configured:
        _dry_run_notice(settings)
        console.print(f"\n[dim]Request was:[/dim] {request}")
        return

    orchestrator = build_default_orchestrator(settings)
    result = orchestrator.handle(request)

    if result.tool_invocations:
        console.print("[dim]Tool invocations:[/dim]")
        for inv in result.tool_invocations:
            status = "[green]ok[/green]" if inv["ok"] else "[red]failed[/red]"
            console.print(f"  - {inv['tool']} ({status})")
    console.print(Panel(result.final_text, title="Result"))


@app.command()
def run(request: str = typer.Argument(..., help="Natural-language request.")) -> None:
    """Execute a single request and print the result."""
    _run_once(request)


@app.command()
def info() -> None:
    """Show resolved configuration and the registered agents."""
    settings = get_settings()
    console.print(
        Panel.fit(
            f"Provider: [bold]{settings.llm_provider}[/bold] "
            f"(model: {settings.active_model})\n"
            f"LLM configured: {settings.llm_configured}\n"
            f"Snowflake configured: {settings.snowflake_configured}\n"
            f"Excel models dir: {settings.excel_models_dir}\n"
            f"VBA scripts dir: {settings.vba_scripts_dir}",
            title="Configuration",
        )
    )
    registry = build_registry(settings)
    for s in registry.tool_specs():
        console.print(f"  - [bold]{s.name}[/bold]: {s.description}")


@app.command()
def repl() -> None:
    """Start an interactive prompt loop."""
    settings = get_settings()
    console.print(
        Panel.fit(
            "PennyMac Trading Desktop Agent. Type a request, or 'exit' to quit.",
            title="Interactive",
        )
    )
    if not settings.llm_configured:
        _dry_run_notice(settings)
        return
    orchestrator = build_default_orchestrator(settings)
    while True:
        try:
            request = console.input("[bold cyan]trader>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye.")
            break
        if request.lower() in {"exit", "quit", ":q"}:
            break
        if not request:
            continue
        result = orchestrator.handle(request)
        console.print(Panel(result.final_text, title="Result"))


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    """Default to the interactive REPL when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        repl()


if __name__ == "__main__":
    app()
