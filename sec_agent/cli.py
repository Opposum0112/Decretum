"""Typer command-line interface for Decretum."""
from __future__ import annotations

from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from .compiler import compile_recipe, dispatch
from .triage import run_triage
from .validator import validate_recipe

app = typer.Typer(help="Decretum declarative security research agent")
console = Console()


@app.command()
def validate(recipe: Path) -> None:
    """Validate a recipe and run non-destructive host pre-flight checks."""
    _, errors, warnings = validate_recipe(recipe)
    table = Table(title="Validation")
    table.add_column("Level")
    table.add_column("Message")
    for error in errors:
        table.add_row("ERROR", error)
    for warning in warnings:
        table.add_row("PREFLIGHT", warning)
    if not errors and not warnings:
        table.add_row("OK", "Recipe structure and host write check passed")
    console.print(table)
    raise typer.Exit(1 if errors else 0)


@app.command()
def run(recipe: Path, interactive: bool = False, dry_run: bool = True) -> None:
    """Compile and execute a recipe. Dry-run defaults to true."""
    data, errors, warnings = validate_recipe(recipe)
    if errors:
        for item in errors:
            console.print(f"[red]ERROR[/red] {item}")
        raise typer.Exit(1)
    if warnings:
        for item in warnings:
            console.print(f"[yellow]PREFLIGHT[/yellow] {item}")
    contract = compile_recipe(data, Path("artifacts") / data["id"])
    console.print(f"Contract: {contract.contract_id}")
    code = dispatch(contract, dry_run=dry_run)
    if code:
        raise typer.Exit(code)
    if interactive:
        run_triage(contract.artifact_dir)


@app.command()
def triage(artifacts: Path) -> None:
    """Interactively inspect already captured artifacts offline."""
    run_triage(artifacts)


if __name__ == "__main__":
    app()
