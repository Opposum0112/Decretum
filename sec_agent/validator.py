"""Local-only LinkML-aligned recipe validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROLE_VALUES = {
    "threat_researcher",
    "supply_chain_auditor",
    "detection_engineer",
    "vulnerability_exploit_researcher",
}
TOOLS = {"tetragon", "bpftrace", "strace", "tcpdump", "tshark"}
BACKENDS = {"unix", "docker"}


def load_recipe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Recipe root must be a YAML mapping")
    return value


def structural_validate(recipe: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"id", "name", "version", "role", "objective", "environment", "policy", "evidence", "completion"}
    errors.extend(f"missing required field: {key}" for key in sorted(required - recipe.keys()))

    if recipe.get("role") not in ROLE_VALUES:
        errors.append(f"invalid role: {recipe.get('role')!r}")

    environment = recipe.get("environment")
    if not isinstance(environment, dict):
        errors.append("environment must be a mapping")
        return errors

    if environment.get("type", "local") != "local":
        errors.append("environment.type must be local; hosted sandbox execution is not supported")

    sandbox = environment.get("sandbox")
    if not isinstance(sandbox, dict):
        errors.append("environment.sandbox must be a mapping")
    else:
        backend = sandbox.get("backend")
        if backend not in BACKENDS:
            errors.append("environment.sandbox.backend must be unix or docker")
        if backend == "docker" and not sandbox.get("image"):
            errors.append("Docker sandbox requires environment.sandbox.image")
        if sandbox.get("inherit_host_environment", False):
            errors.append("host environment inheritance must remain disabled")

    if environment.get("privileged", False):
        errors.append("privileged execution is prohibited by default")

    policy = recipe.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be a mapping")
    else:
        for key in ("allow", "deny", "approval_required"):
            if policy.get(key) is not None and not isinstance(policy[key], list):
                errors.append(f"policy.{key} must be a list")

    evidence = recipe.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be a mapping")
    elif not evidence.get("required"):
        errors.append("evidence.required must be non-empty")

    completion = recipe.get("completion")
    if not isinstance(completion, dict):
        errors.append("completion must be a mapping")
    elif completion.get("report_required", True) is not True:
        errors.append("completion.report_required must remain true")

    instrumentation = recipe.get("instrumentation", {})
    if instrumentation is not None and not isinstance(instrumentation, dict):
        errors.append("instrumentation must be a mapping")
    elif isinstance(instrumentation, dict):
        for tool in instrumentation.get("tools", []) or []:
            if tool not in TOOLS:
                errors.append(f"unsupported instrumentation tool: {tool!r}")

    return errors


def preflight(recipe: dict[str, Any]) -> list[str]:
    environment = recipe.get("environment", {})
    sandbox = environment.get("sandbox", {}) if isinstance(environment, dict) else {}
    backend = sandbox.get("backend")
    if backend == "docker":
        return ["Docker backend selected: local Docker daemon must be available"]
    if backend == "unix":
        return ["Unix-local backend selected: commands execute with host permissions; use only for trusted workloads or an externally isolated host"]
    return []


def validate_recipe(path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    recipe = load_recipe(path)
    errors = structural_validate(recipe)
    return recipe, errors, preflight(recipe) if not errors else []
