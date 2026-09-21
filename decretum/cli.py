"""CLI for the Decretum declarative execution compiler.

The CLI deliberately stops at validation, discovery, resolution and compilation.
It never starts an agent/harness runtime or owns research state.
"""
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .capability_discovery import discover_capability_surfaces, write_candidate_yaml, write_discovery_report
from .capability_registry import canonical_capabilities, candidate, promote_capability
from .compiler import compile_execution_contract, write_contract
from .domain_packs import installed_pack_summary, validate_pack_directory
from .resolver import resolve_capabilities
from .validator import validate_recipe

app = typer.Typer(help="Decretum: domain-neutral declarative execution compiler")
capabilities_app = typer.Typer(help="Discover and inspect capability execution surfaces.")
spec_app = typer.Typer(help="Compile human-authored Markdown specifications.")
app.add_typer(spec_app, name="spec")
app.add_typer(capabilities_app, name="capabilities")
console = Console()


@capabilities_app.command("discover")
def discover_capabilities(
    recipe: Path | None = typer.Option(None, "--recipe", help="Optional recipe used to generate capability candidates."),
    output: Path = typer.Option(Path("artifacts/capability-discovery"), "--output"),
) -> None:
    """Discover local execution surfaces without changing canonical capability semantics."""
    from .validator import load_recipe

    recipe_data = load_recipe(recipe) if recipe else None
    report = discover_capability_surfaces(recipe=recipe_data)
    report_path = write_discovery_report(report, output)
    candidate_path = write_candidate_yaml(report, output)
    console.print(f"Discovery manifest: {report_path}")
    console.print(f"Surfaces discovered: {len(report.get('surfaces', []))}")
    console.print(f"Ready surfaces: {sum(1 for item in report.get('surfaces', []) if item.get('ready'))}")
    if candidate_path:
        console.print(f"Candidates requiring review: {candidate_path}")
    console.print("Canonical capability schema was not modified.")


@capabilities_app.command("list")
def list_capabilities() -> None:
    """List researcher-approved canonical capabilities."""
    capabilities = canonical_capabilities()
    table = Table(title="Canonical capabilities")
    table.add_column("Capability")
    table.add_column("Kind")
    table.add_column("Risk")
    table.add_column("Description")
    for cid, spec in sorted(capabilities.items()):
        table.add_row(cid, str(spec.get("kind", "")), str(spec.get("risk", "")), str(spec.get("description", "")))
    console.print(table if capabilities else "No promoted capabilities are registered yet.")


@capabilities_app.command("approve")
def approve_capability(
    capability_id: str = typer.Argument(...),
    domain: str = typer.Option(..., "--domain", help="Domain provided by the installed domain pack."),
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
    """Explicitly promote reviewed semantics into the canonical capability vocabulary."""
    existing_candidate = candidate(candidate_file, capability_id) if candidate_file.exists() else None
    if existing_candidate is None:
        console.print(f"[yellow]No discovery candidate found for {capability_id!r}; using explicitly authored semantics.[/yellow]")
    spec = {
        "id": capability_id,
        "name": name,
        "kind": kind,
        "risk": risk,
        "description": description,
        "requires_approval": risk in {"execute", "write", "privileged", "network_access"},
        "evidence_outputs": evidence_output,
        "allowed_isolations": allowed_isolation,
        "allowed_networks": allowed_network,
        "allowed_execution_modes": allowed_execution_mode,
    }
    try:
        promote_capability(spec, domain=domain)
    except ValueError as exc:
        console.print(f"[red]ERROR[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"[green]Approved canonical capability:[/green] {capability_id}")
    console.print("Provider implementations still require explicit registration.")




@spec_app.command("packs")
def list_domain_packs() -> None:
    """List installed Decretum domain packs."""
    console.print_json(json.dumps(installed_pack_summary()))

@spec_app.command("validate-pack")
def validate_domain_pack(path: Path) -> None:
    """Validate a local domain-pack directory before packaging."""
    errors = validate_pack_directory(path)
    if errors:
        for item in errors:
            console.print(f"[red]ERROR[/red] {item}")
        raise typer.Exit(1)
    console.print(f"[green]OK[/green] domain pack: {path}")

@spec_app.command("compile")
def spec_compile(spec: Path, output: Path = Path("recipe.yaml")) -> None:
    """Compile a human-authored Markdown spec into an ExecutionRecipe."""
    from .spec_compiler import compile_spec, write_recipe

    try:
        recipe = compile_spec(spec)
        write_recipe(recipe, output)
    except (OSError, ValueError) as exc:
        console.print(f"[red]ERROR[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(f"Recipe: {output}")
    console.print("Next: decretum validate <recipe.yaml>")


@app.command()
def validate(recipe: Path) -> None:
    """Validate a recipe; nothing is executed."""
    _, errors, findings = validate_recipe(recipe)
    table = Table(title="Recipe validation")
    table.add_column("Level")
    table.add_column("Message")
    for item in errors:
        table.add_row("ERROR", item)
    for item in findings:
        table.add_row("PREFLIGHT", item)
    if not errors and not findings:
        table.add_row("OK", "Recipe is valid for resolution and compilation")
    console.print(table)
    raise typer.Exit(1 if errors else 0)


@app.command("resolve")
def resolve(recipe: Path) -> None:
    """Resolve capabilities, providers, integrations, surfaces and harness compatibility without executing."""
    from .validator import load_recipe

    result = resolve_capabilities(load_recipe(recipe))
    console.print_json(json.dumps(result))
    raise typer.Exit(0 if result.get("status") == "ready" else 1)


@app.command("compile")
def compile_contract(recipe: Path, output: Path | None = None) -> None:
    """Compile a portable ExecutionContract for an external harness runtime."""
    data, errors, _ = validate_recipe(recipe)
    if errors:
        for item in errors:
            console.print(f"[red]ERROR[/red] {item}")
        raise typer.Exit(1)
    contract = compile_execution_contract(data, Path("artifacts") / data["id"])
    path = write_contract(contract)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(contract.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        path = output
    console.print(f"Contract: {contract.contract_id}")
    console.print(f"Wrote: {path}")
    console.print("Decretum stops here. Pass the contract to a compatible harness runtime.")


@app.command("handoff")
def handoff(contract: Path) -> None:
    """Validate and print a compiled contract handoff envelope; never execute it."""
    data = json.loads(contract.read_text(encoding="utf-8"))
    required = {"apiVersion", "kind", "contract_version", "contract_id", "capabilities", "handoff"}
    missing = sorted(required - set(data))
    if missing:
        console.print(f"[red]ERROR[/red] contract missing fields: {', '.join(missing)}")
        raise typer.Exit(1)
    if data["kind"] not in {"ExecutionContract"}:
        console.print("[red]ERROR[/red] unsupported contract kind")
        raise typer.Exit(1)
    envelope = {
        "protocol": "decretum.dev/v1",
        "type": "execution_handoff",
        "contract": data,
        "execution": "external_harness_runtime",
        "decretum_action": "none_after_handoff",
    }
    console.print_json(json.dumps(envelope))
