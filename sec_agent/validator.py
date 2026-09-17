"""Recipe schema validation and host pre-flight checks."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from rich.console import Console

console = Console()

ROLE_VALUES = {
    "threat_researcher",
    "supply_chain_auditor",
    "detection_engineer",
    "vulnerability_exploit_researcher",
}
PROVIDERS = {"lima", "podman"}
HARNESS = {"goose", "pi", "headless"}
TOOLS = {"tetragon", "bpftrace", "strace", "tcpdump", "tshark"}


def load_recipe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError("Recipe root must be a YAML mapping")
    return value


def structural_validate(recipe: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"id", "name", "version", "role", "objective", "harness", "compute", "evidence", "workload"}
    errors.extend(f"missing required field: {key}" for key in sorted(required - recipe.keys()))
    if recipe.get("role") not in ROLE_VALUES:
        errors.append(f"invalid role: {recipe.get('role')!r}")
    if recipe.get("harness") not in HARNESS:
        errors.append(f"invalid harness: {recipe.get('harness')!r}")
    compute = recipe.get("compute")
    if not isinstance(compute, dict):
        errors.append("compute must be a mapping")
    else:
        if compute.get("provider") not in PROVIDERS:
            errors.append(f"invalid compute.provider: {compute.get('provider')!r}")
        if not isinstance(compute.get("cpus"), int) or compute.get("cpus", 0) < 1:
            errors.append("compute.cpus must be an integer >= 1")
        if compute.get("allow_host_mounts", False) is not False:
            errors.append("host mounts are prohibited")
    evidence = recipe.get("evidence")
    if not isinstance(evidence, dict) or not evidence.get("artifact_paths"):
        errors.append("evidence.artifact_paths must be non-empty")
    if isinstance(evidence, dict) and evidence.get("hash_algorithm", "sha256") != "sha256":
        errors.append("only sha256 evidence manifests are supported")
    workload = recipe.get("workload")
    if not isinstance(workload, dict) or not isinstance(workload.get("command"), str):
        errors.append("workload.command must be a string")
    instrumentation = recipe.get("instrumentation", {})
    if isinstance(instrumentation, dict):
        for tool in instrumentation.get("tools", []):
            if tool not in TOOLS:
                errors.append(f"unsupported instrumentation tool: {tool!r}")
    return errors


def preflight(recipe: dict[str, Any], artifact_dir: Path) -> list[str]:
    """Return warnings/errors without executing the workload."""
    findings: list[str] = []
    provider = recipe.get("compute", {}).get("provider") if isinstance(recipe.get("compute"), dict) else None
    if provider == "lima" and shutil.which("limactl") is None:
        findings.append("limactl not found on PATH")
    if provider == "podman" and shutil.which("podman") is None:
        findings.append("podman not found on PATH")
    harness = recipe.get("harness")
    if harness in {"goose", "pi"} and shutil.which(harness) is None:
        findings.append(f"{harness} CLI not found on PATH")
    for tool in recipe.get("instrumentation", {}).get("tools", []):
        if shutil.which(tool) is None and importlib.util.find_spec(tool) is None:
            findings.append(f"instrumentation dependency not found: {tool}")
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        probe = artifact_dir / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        findings.append(f"artifact directory is not writable: {exc}")
    return findings


def validate_recipe(path: Path, artifact_dir: Path = Path("artifacts")) -> tuple[dict[str, Any], list[str], list[str]]:
    recipe = load_recipe(path)
    errors = structural_validate(recipe)
    warnings = preflight(recipe, artifact_dir) if not errors else []
    return recipe, errors, warnings
