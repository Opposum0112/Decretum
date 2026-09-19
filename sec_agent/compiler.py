"""Compile Decretum research recipes into portable machine-readable contracts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .resolver import resolve_capabilities
from .validator import (
    DEFAULT_PROVIDER_REGISTRY,
    load_provider_registry,
    provider_capability_index,
)

@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    contract: dict[str, Any]
    artifact_dir: Path


def _required_capabilities(recipe: dict[str, Any]) -> dict[str, list[str]]:
    """Derive capability requirements from the recipe, using the registry as source of truth."""
    required = {"artifact.read", "artifact.collect"}
    workload = recipe.get("workload", {}) or {}
    if workload.get("command"):
        required.add("process.execute")

    for skill in recipe.get("skills", []) or []:
        required.update(skill.get("capabilities", []) or [])

    role = recipe.get("role_definition", {}) or {}
    required.update(role.get("default_capabilities", []) or [])

    environment = recipe.get("environment", {}) or {}
    compute = environment.get("compute", {}) or {}
    sandbox = environment.get("sandbox", {}) or {}
    provider_id = compute.get("provider") or sandbox.get("backend")

    if provider_id:
        registry = load_provider_registry(str(DEFAULT_PROVIDER_REGISTRY))
        provider = (registry.get("providers", {}) or {}).get(provider_id, {})
        required.update(provider.get("capabilities", []) or [])

    for experiment in recipe.get("experiments", []) or []:
        required.update(experiment.get("capabilities", []) or [])
        capability = experiment.get("capability")
        if capability:
            required.add(capability)

    denied = set((recipe.get("policy", {}) or {}).get("deny", []) or [])
    return {"required": sorted(required), "denied": sorted(denied)}


def _experiment_steps(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize optional experiment composition into a stable execution IR."""
    steps = []
    for index, item in enumerate(recipe.get("experiments", []) or []):
        step = {
            "id": item["id"],
            "capabilities": sorted(set(item.get("capabilities", []) or ([] if not item.get("capability") else [item["capability"]]))),
            "depends_on": list(item.get("depends_on", []) or []),
            "inputs": item.get("inputs", {}),
            "outputs": item.get("outputs", []),
            "objective": item.get("objective", ""),
            "approval_required": bool(item.get("approval_required", False)),
            "ordinal": index,
        }
        steps.append(step)
    return steps


def _interface_bindings(recipe: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    """Resolve capabilities to concrete provider/interface/harness combinations."""
    resolution = resolve_capabilities(recipe, registry_path)
    bindings = []
    for item in resolution.get("capabilities", []):
        if item.get("status") == "unavailable":
            continue
        for provider in item.get("providers", []):
            for harness in provider.get("harnesses", []):
                bindings.append({
                    "capability": item["capability"],
                    "provider": provider["provider"],
                    "interface": provider["interface"],
                    "harness": harness,
                    "available": provider.get("available", False),
                })
    return {
        "status": resolution.get("status"),
        "bindings": bindings,
        "harnesses": resolution.get("harnesses", []),
        "integrations": resolution.get("integrations", []),
        "models": resolution.get("models", []),
    }


def compile_recipe(
    recipe: dict[str, Any],
    artifact_dir: Path,
    registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
) -> ExecutionContract:
    role_definition = recipe.get("role_definition", {}) or {}
    skills = recipe.get("skills", []) or []
    execution = _interface_bindings(recipe, registry_path)

    body = {
        "apiVersion": "decretum.dev/v1",
        "kind": "ResearchExecutionContract",
        "contract_version": "2",
        "research": {
            "id": recipe["id"],
            "name": recipe["name"],
            "version": recipe["version"],
            "role": recipe["role"],
            "objective": recipe["objective"],
            "references": recipe.get("references", []),
        },
        "inputs": recipe.get("inputs", {}),
        "environment": recipe["environment"],
        "roles": [{
            "id": recipe["role"],
            "definition": role_definition,
            "skills": role_definition.get("skills", [s.get("id") for s in skills]),
            "default_capabilities": role_definition.get("default_capabilities", []),
            "allowed_tools": role_definition.get("allowed_tools", []),
        }],
        "skills": skills,
        "skill_catalog": recipe.get("skill_catalog", []),
        "capability_catalog": recipe.get("capability_catalog", []),
        "capability_requirements": _required_capabilities(recipe),
        "capability_graph": [{
            "skill": s.get("id"),
            "capabilities": s.get("capabilities", []) or [],
            "tools": s.get("tools", []) or [],
            "evidence_inputs": s.get("evidence_inputs", []) or [],
            "evidence_outputs": s.get("evidence_outputs", []) or [],
        } for s in skills],
        "experiment_graph": {
            "steps": _experiment_steps(recipe),
            "entrypoints": [
                step["id"] for step in _experiment_steps(recipe)
                if not step["depends_on"]
            ],
        },
        "resolution": execution,
        "provider_registry": "schema/provider_registry.yaml",
        "provider_interfaces": ["mcp", "api", "tool"],
        "orchestration": recipe["environment"].get(
            "orchestration", {"executor": "codex", "mode": "interactive"}
        ),
        "policy": recipe["policy"],
        "evidence": recipe["evidence"],
        "completion": recipe["completion"],
        "workload": recipe.get("workload", {}),
        "reports": recipe.get("reports", []),
    }

    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    contract_id = hashlib.sha256(canonical).hexdigest()[:16]
    return ExecutionContract(
        contract_id,
        {**body, "contract_id": contract_id},
        artifact_dir,
    )


def write_contract(contract: ExecutionContract) -> Path:
    contract.artifact_dir.mkdir(parents=True, exist_ok=True)
    path = contract.artifact_dir / "research-contract.json"
    path.write_text(
        json.dumps(contract.contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
