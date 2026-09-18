"""CLI for the declarative Decretum → OpenAI research workflow."""
from __future__ import annotations
import json
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from .compiler import compile_recipe, write_contract
from .openai_runner import create_session, save_session
from .validator import validate_recipe

app = typer.Typer(help="Decretum: declarative security research for OpenAI Agents API")
console = Console()

@app.command()
def validate(recipe: Path) -> None:
    """Validate a YAML research recipe."""
    _, errors, findings = validate_recipe(recipe)
    table = Table(title="Recipe validation")
    table.add_column("Level"); table.add_column("Message")
    for item in errors: table.add_row("ERROR", item)
    for item in findings: table.add_row("PREFLIGHT", item)
    if not errors and not findings: table.add_row("OK", "Recipe is valid and ready for compilation")
    console.print(table)
    raise typer.Exit(1 if errors else 0)

@app.command("compile")
def compile_contract(recipe: Path, output: Path | None = None) -> None:
    """Validate and compile a recipe without executing it."""
    data, errors, _ = validate_recipe(recipe)
    if errors:
        for item in errors: console.print(f"[red]ERROR[/red] {item}")
        raise typer.Exit(1)
    contract = compile_recipe(data, output.parent if output else Path("artifacts") / data["id"])
    path = write_contract(contract)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(contract.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path = output
    console.print(f"Contract: {contract.contract_id}")
    console.print(f"Wrote: {path}")

@app.command()
def run(recipe: Path, model: str | None = None, dry_run: bool = True) -> None:
    """Compile a recipe and, unless dry-run, start an OpenAI-managed research session."""
    data, errors, findings = validate_recipe(recipe)
    if errors:
        for item in errors: console.print(f"[red]ERROR[/red] {item}")
        raise typer.Exit(1)
    for item in findings: console.print(f"[yellow]PREFLIGHT[/yellow] {item}")
    contract = compile_recipe(data, Path("artifacts") / data["id"])
    path = write_contract(contract)
    console.print(f"Contract: {contract.contract_id}")
    console.print(f"Wrote: {path}")
    if dry_run:
        console.print("[cyan]DRY RUN[/cyan] No OpenAI session was created.")
        return
    session = create_session(contract.contract, model=model)
    session_path = save_session(session, contract.artifact_dir)
    console.print(f"OpenAI session: {session.id}")
    console.print(f"Session state: {session.status}")
    console.print(f"Saved: {session_path}")

@app.command()
def inspect(recipe_id: str) -> None:
    """Inspect locally persisted research state."""
    root = Path("artifacts") / recipe_id
    if not root.exists(): raise typer.BadParameter(f"No research state found at {root}")
    console.print(root)
    for path in sorted(root.iterdir()): console.print(f" - {path.name}")

if __name__ == "__main__":
    app()
