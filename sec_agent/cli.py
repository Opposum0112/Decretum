"""CLI for the local-only Decretum research workflow."""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .compiler import compile_recipe, write_contract
from .openai_runner import create_session, save_session\nfrom .research_state import append_event, evidence_context
from .validator import validate_recipe

app = typer.Typer(help="Decretum: declarative local security research executed by Codex")
console = Console()


@app.command()
def validate(recipe: Path) -> None:
    """Validate a YAML research recipe."""
    _, errors, findings = validate_recipe(recipe)
    table = Table(title="Recipe validation")
    table.add_column("Level")
    table.add_column("Message")
    for item in errors:
        table.add_row("ERROR", item)
    for item in findings:
        table.add_row("PREFLIGHT", item)
    if not errors and not findings:
        table.add_row("OK", "Recipe is valid and ready for local execution")
    console.print(table)
    raise typer.Exit(1 if errors else 0)


@app.command("compile")
def compile_contract(recipe: Path, output: Path | None = None) -> None:
    """Validate and compile a recipe without executing it."""
    data, errors, _ = validate_recipe(recipe)
    if errors:
        for item in errors:
            console.print(f"[red]ERROR[/red] {item}")
        raise typer.Exit(1)
    contract = compile_recipe(data, Path("artifacts") / data["id"])
    path = write_contract(contract)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(contract.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path = output
    console.print(f"Contract: {contract.contract_id}")
    console.print(f"Wrote: {path}")


@app.command()
def run(recipe: Path, model: str | None = None, dry_run: bool = True) -> None:
    """Compile and, unless dry-run, execute the contract through local Codex."""
    data, errors, findings = validate_recipe(recipe)
    if errors:
        for item in errors:
            console.print(f"[red]ERROR[/red] {item}")
        raise typer.Exit(1)
    for item in findings:
        console.print(f"[yellow]PREFLIGHT[/yellow] {item}")

    contract = compile_recipe(data, Path("artifacts") / data["id"])
    path = write_contract(contract)
    console.print(f"Contract: {contract.contract_id}")
    console.print(f"Wrote: {path}")

    if dry_run:
        console.print("[cyan]DRY RUN[/cyan] No local sandbox or model session was started.")
        return

    session = create_session(
        contract.contract,
        workspace=recipe.parent.resolve(),
        model=model,
    )
    session_path = save_session(session, contract.artifact_dir)
    console.print("Codex research completed in the local workspace.")
    console.print(f"Saved: {session_path}")


@app.command()
def analyze(recipe_id: str, question: str, model: str | None = None) -> None:
    """Continue interactive analysis of accumulated evidence in an existing research session."""
    root = Path("artifacts") / recipe_id
    contract_path = root / "research-contract.json"
    if not contract_path.exists():
        raise typer.BadParameter(f"No compiled research contract found at {contract_path}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    workspace = Path(contract.get("environment", {}).get("sandbox", {}).get("workspace_directory") or ".").resolve()
    session = create_session(
        contract,
        workspace=workspace,
        model=model,
        prompt=question,
        session_db=root / "research-session.sqlite3",
    )
    path = save_session(session, root)
    console.print(getattr(session, "final_output", session))
    console.print(f"Saved: {path}")


@app.command()
def inspect(recipe_id: str) -> None:
    """Inspect locally persisted research state."""
    root = Path("artifacts") / recipe_id
    if not root.exists():
        raise typer.BadParameter(f"No research state found at {root}")
    console.print(root)
    for path in sorted(root.iterdir()):
        console.print(f" - {path.name}")


if __name__ == "__main__":
    app()
