"""Recipe validation and host capability pre-flight checks."""
from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console

console = Console()

ROLE_VALUES = {
    "threat_researcher",
    "supply_chain_auditor",
    "detection_engineer",
    "vulnerability_exploit_researcher",
}
PROVIDERS = {"lima", "podman", "docker"}
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
    """Validate recipe shape and safety invariants without touching the host."""
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
        if not isinstance(compute.get("base_image"), str) or not compute.get("base_image", "").strip():
            errors.append("compute.base_image must be a non-empty string")
        if not isinstance(compute.get("memory"), str) or not compute.get("memory", "").strip():
            errors.append("compute.memory must be a non-empty string")
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
    if not isinstance(workload, dict) or not isinstance(workload.get("command"), str) or not workload.get("command", "").strip():
        errors.append("workload.command must be a non-empty string")
    if isinstance(workload, dict) and (not isinstance(workload.get("timeout_seconds", 300), int) or workload.get("timeout_seconds", 300) < 1):
        errors.append("workload.timeout_seconds must be an integer >= 1")
    instrumentation = recipe.get("instrumentation", {})
    if instrumentation is not None and not isinstance(instrumentation, dict):
        errors.append("instrumentation must be a mapping")
    elif isinstance(instrumentation, dict):
        for tool in instrumentation.get("tools", []):
            if tool not in TOOLS:
                errors.append(f"unsupported instrumentation tool: {tool!r}")
    return errors


def _require_cli(findings: list[str], executable: str, purpose: str) -> None:
    if shutil.which(executable) is None:
        findings.append(f"{purpose}: {executable} not found on PATH")


def _check_compute_capability(recipe: dict[str, Any], findings: list[str]) -> None:
    provider = recipe.get("compute", {}).get("provider") if isinstance(recipe.get("compute"), dict) else None
    if provider == "lima":
        _require_cli(findings, "limactl", "compute provider")
    elif provider == "podman":
        _require_cli(findings, "podman", "compute provider")
        if shutil.which("podman"):
            probe = shutil.which("podman")
            assert probe
            result = __import__("subprocess").run([probe, "info", "--format", "{{.Host.Security.Rootless}}"], capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                findings.append("podman is installed but the engine is not usable")
            elif result.stdout.strip().lower() not in {"true", "1"}:
                findings.append("podman must run rootless for Decretum workloads")
    elif provider == "docker":
        _require_cli(findings, "docker", "compute provider")
        if shutil.which("docker"):
            result = __import__("subprocess").run(["docker", "info"], capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                findings.append("docker CLI is installed but the Docker daemon is not reachable")


def _check_instrumentation(recipe: dict[str, Any], findings: list[str]) -> None:
    instrumentation = recipe.get("instrumentation") or {}
    for tool in instrumentation.get("tools", []):
        if shutil.which(tool) is None and importlib.util.find_spec(tool) is None:
            findings.append(f"instrumentation dependency not found: {tool}")


def _check_harness(recipe: dict[str, Any], findings: list[str]) -> None:
    harness = recipe.get("harness")
    if harness in {"goose", "pi"}:
        _require_cli(findings, harness, "harness")


def _check_artifact_dir(artifact_dir: Path, findings: list[str]) -> None:
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        probe = artifact_dir / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        findings.append(f"artifact directory is not writable: {exc}")


def preflight(recipe: dict[str, Any], artifact_dir: Path) -> list[str]:
    """Check host capabilities required by a structurally valid recipe.

    This function is read-only with respect to workloads: it never executes the
    recipe command. Its findings are intended to hard-gate compilation/dispatch.
    """
    findings: list[str] = []
    _check_compute_capability(recipe, findings)
    _check_harness(recipe, findings)
    _check_instrumentation(recipe, findings)
    _check_artifact_dir(artifact_dir, findings)
    return findings


def validate_recipe(path: Path, artifact_dir: Path = Path("artifacts")) -> tuple[dict[str, Any], list[str], list[str]]:
    recipe = load_recipe(path)
    errors = structural_validate(recipe)
    findings = preflight(recipe, artifact_dir) if not errors else []
    return recipe, errors, findings
