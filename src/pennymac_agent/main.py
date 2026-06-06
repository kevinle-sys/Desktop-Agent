"""Command-line entry point for the PennyMac Trading Desktop Agent (CrewAI).

Usage:
    python -m pennymac_agent crew "..."            # hierarchical, manager-led
    python -m pennymac_agent agent data_analyst "..."   # one specialist directly
    python -m pennymac_agent info                  # show config + agents/tools
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from .config.settings import get_settings

app = typer.Typer(
    add_completion=False,
    help="PennyMac Trading Desktop Agent - CrewAI multi-agent framework.",
)
console = Console()

_SPECIALIST_TOOLS = {
    "data_analyst": ["snowflake_query", "sqlserver_query"],
    "excel_modeler": ["excel_model"],
    "automation_engineer": ["run_vba_macro", "generate_vba"],
}


def _require_llm() -> bool:
    settings = get_settings()
    if settings.llm_configured:
        return True
    console.print(
        Panel.fit(
            f"[yellow]Not configured[/yellow]: LLM provider "
            f"'[bold]{settings.llm_provider}[/bold]' has no API key set.\n"
            "Add the key to your .env to run the crew. Showing agents/tools "
            "via `info` still works.",
            title="Dry run",
        )
    )
    return False


@app.command()
def crew(prompt: str = typer.Argument(..., help="Natural-language request.")) -> None:
    """Run the hierarchical, manager-led crew."""
    if not _require_llm():
        return
    from .crew import run_crew

    result = run_crew(prompt)
    console.print(Panel(result, title="Crew result"))


@app.command()
def agent(
    name: str = typer.Argument(..., help="Specialist key, e.g. data_analyst."),
    prompt: str = typer.Argument(..., help="Natural-language request."),
) -> None:
    """Run a single specialist agent directly."""
    if name not in _SPECIALIST_TOOLS:
        console.print(
            f"[red]Unknown specialist '{name}'.[/red] Available: "
            f"{list(_SPECIALIST_TOOLS)}"
        )
        raise typer.Exit(code=1)
    if not _require_llm():
        return
    from .crew import run_specialist

    result = run_specialist(name, prompt)
    console.print(Panel(result, title=f"{name} result"))


@app.command()
def info() -> None:
    """Show resolved configuration and the registered agents and tools."""
    settings = get_settings()
    console.print(
        Panel.fit(
            f"Provider: [bold]{settings.llm_provider}[/bold] "
            f"(model: {settings.active_model})\n"
            f"LLM configured: {settings.llm_configured}\n"
            f"Snowflake configured: {settings.snowflake_configured}\n"
            f"SQL Server configured: {settings.sqlserver_configured}\n"
            f"Excel models dir: {settings.excel_models_dir}\n"
            f"Artifacts dir: {settings.artifacts_dir}",
            title="Configuration",
        )
    )
    console.print("[bold]Specialists (run directly via `agent <name>`):[/bold]")
    for key, tools in _SPECIALIST_TOOLS.items():
        console.print(f"  - [bold]{key}[/bold]: tools = {', '.join(tools)}")
    console.print(
        "\n[dim]Or use `crew \"<prompt>\"` to let a manager delegate across "
        "all specialists.[/dim]"
    )


@app.callback(invoke_without_command=True)
def _default(ctx: typer.Context) -> None:
    """Show help when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
