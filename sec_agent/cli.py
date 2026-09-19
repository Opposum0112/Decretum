"""CLI for the local-only Decretum research workflow."""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .compiler import compile_recipe, write_contract
from .capability_discovery import discover_capability_surfaces, write_candidate_yaml, write_discovery_report
from .capability_registry import canonical_capabilities, candidate, promote_capability
from .harness_adapters import get_adapter, available_adapters
from .openai_runner import create_session, save_session
from .research_state import append_event, evidence_context, record_execution, record_execution_result, verify_ledger
from .resolver import resolve_capabilities
from .validator import validate_recipe

app = typer.Typer(help="Decretum: declarative local security research compiler")
capabilities_app = typer.Typer(help="Discover and inspect capability execution surfaces.")
app.add_typer(capabilities_app, name="capabilities")
console = Console()


@capabilities_app.command("discover")
def discover_capabilities(
    recipe: Path | None = typer.Option(
        None, "--recipe", help="Optional recipe used to generate missing-capability candidates."
    ),
    output: Path = typer.Option(Path("artifacts/capability-discovery"), "--output"),
) -> None:
    """Discover local provider/harness execution surfaces without changing the canonical schema."""
    from .validator import load_recipe

    recipe_data = load_recipe(recipe) if recipe else None
    report = discover_capability_surfaces(recipe=recipe_data)
    report_path = write_discovery_report(report, output)
    candidate_path = write_candidate_yaml(report, output)
    console.print(f"Discovery manifest: {report_path}")
    console.print(f"Surfaces discovered: {len(report.get('surfaces', []))}")
    ready = sum(1 for item in report.get("surfaces", []) if item.get("ready"))
    console.print(f"Ready surfaces: {ready}")
    if candidate_path:
        console.print(f"Candidates requiring review: {candidate_path}")
    console.print("Canonical schema was not modified.")




@capabilities_app.command("list")
def list_capabilities() -> None:
    """List researcher-approved canonical capabilities available to recipes."""
    capabilities = canonical_capabilities()
    table = Table(title="Canonical capabilities")
    table.add_column("Capability")
    table.add_column("Kind")
    table.add_column("Risk")
    table.add_column("Description")
    for cid, spec in sorted(capabilities.items()):
        table.add_row(cid, str(spec.get("kind", "")), str(spec.get("risk", "")), str(spec.get("description", "")))
    if capabilities:
        console.print(table)
    else:
        console.print("No promoted capabilities are registered yet.")


@capabilities_app.command("approve")
def approve_capability(
    capability_id: str = typer.Argument(..., help="Candidate capability id, e.g. cloud.audit.query."),
    candidate_file: Path = typer.Option(Path("artifacts/capability-discovery/capability-candidates.yaml"), "--candidate"),
    kind: str = typer.Option(..., "--kind"),
    risk: str = typer.Option(..., "--risk"),
    name: str = typer.Option(..., "--name"),
    description: str = typer.Option(..., "--description"),
    evidence_output: list[str] = typer.Option([], "--evidence-output"),
    allowed_isolation: list[str] = typer.Option([], "--allowed-isolation"),
    allowed_network: list[str] = typer.Option([], "--allowed-network"),
    allowed_execution_mode: list[str] = typer.Option([], "--allowed-execution-mode"),
) -> None:
    """Explicitly promote a reviewed candidate into the canonical recipe vocabulary."""
    existing_candidate = candidate(candidate_file, capability_id) if candidate_file.exists() else None
    if existing_candidate is None:
        console.print(f"[yellow]No discovery candidate found for {capability_id!r}; approving explicitly authored semantics.[/yellow]")
    spec = {
        "id": capability_id, "name": name, "kind": kind, "risk": risk, "description": description,
        "requires_approval": risk in {"execute", "write", "privileged", "network_access"},
        "evidence_outputs": evidence_output, "allowed_isolations": allowed_isolation,
        "allowed_networks": allowed_network, "allowed_execution_modes": allowed_execution_mode,
    }
    try:
        promote_capability(spec)
    except ValueError as exc:
        console.print(f"[red]ERROR[/red] {exc}")
        raise typer.Exit(1)
    console.print(f"[green]Approved canonical capability:[/green] {capability_id}")
    console.print("Recipes can now reference this capability without redefining its semantics.")
    console.print("Provider implementations still require explicit registration in schema/provider_registry.yaml.")


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


@app.command("resolve")
def resolve(recipe: Path) -> None:
    """Resolve capabilities and show provider/harness/model readiness without executing."""
    data = __import__("sec_agent.validator", fromlist=["load_recipe"]).load_recipe(recipe)
    result = resolve_capabilities(data)
    console.print_json(json.dumps(result))
    raise typer.Exit(0 if result.get("status") == "ready" else 1)


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
        output.write_text(json.dumps(contract.contract, indent=2, sort_keys=True) + "
", encoding="utf-8")
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
