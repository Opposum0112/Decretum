"""Compile Decretum recipes into auditable, portable execution contracts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .resolver import resolve_capabilities
from .validator import DEFAULT_PROVIDER_REGISTRY, required_capabilities\nfrom .registry_snapshot import snapshot_registry
from .manifest import create_manifest
from .environment_plan import plan_environment
from .validator import load_provider_registry


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    contract: dict[str, Any]
    artifact_dir: Path


def _required_capabilities(recipe: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, list[str]]:
    required = required_capabilities(recipe, registry_path)
    denied = set((recipe.get("policy", {}) or {}).get("deny", []) or [])
    return {"required": sorted(required), "denied": sorted(denied)}


def _experiment_steps(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    steps = []
    for step in recipe.get("experiments", []) or []:
        steps.append({
            "id": step["id"],
            "objective": step.get("objective"),
            "capability": step.get("capability"),
            "capabilities": sorted(set(
                list(step.get("capabilities", []) or [])
                + ([step["capability"]] if step.get("capability") else [])
            )),
            "depends_on": sorted(step.get("depends_on", []) or []),
            "inputs": sorted(step.get("inputs", []) or []),
            "outputs": sorted(step.get("outputs", []) or []),
            "approval_required": bool(step.get("approval_required", False)),
        })
    return steps


def _plan_digest(plan: dict[str, Any]) -> str:
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def compile_recipe(
    recipe: dict[str, Any],
    artifact_dir: Path,
    registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
) -> ExecutionContract:
    registry_snapshot = snapshot_registry(registry_path, artifact_dir)
    schema_path = Path(__file__).resolve().parent.parent / "schema" / "sec_research_metamodel.yaml"\n    resolution = resolve_capabilities(recipe, registry_path)
    registry = load_provider_registry(str(registry_path))
    environment_plan = plan_environment(recipe, registry)
    steps = _experiment_steps(recipe)
    experiment_graph = {
        "steps": steps,
        "entrypoints": [step["id"] for step in steps if not step["depends_on"]],
        "execution_order": [step["id"] for step in steps],
    }
    execution_plan = resolution.get("experiment_plan", [])
    approval_plan = {
        "required": sorted({
            capability
            for step in execution_plan
            for capability in step.get("approval_required", [])
        }),
        "steps": [
            step["id"] for step in execution_plan if step.get("approval_required")
        ],
    }
    resolution_audit = {
        "status": resolution.get("status"),
        "capabilities": resolution.get("capabilities", []),
        "failures": resolution.get("failures", []),
        "harnesses": resolution.get("harnesses", []),
        "readiness": resolution.get("readiness", {}),
        "experiment_plan": execution_plan,
    }
    plan_digest = _plan_digest(resolution_audit)

    compilation_manifest = None\n    body = {
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
        "environment_plan": environment_plan,
        "provisioning_plan": environment_plan.get("provisioning", {}),
        "teardown_plan": recipe.get("environment", {}).get("teardown", {"enabled": True, "destroy_ephemeral": True, "collect_evidence_first": True}),
        "analysis_plan": recipe.get("environment", {}).get("analysis", {"enabled": True, "interactive": True}),
        "roles": [{
            "id": recipe["role"],
            "definition": recipe.get("role_definition", {}),
            "skills": (recipe.get("role_definition", {}) or {}).get(
                "skills", [s.get("id") for s in recipe.get("skills", [])]
            ),
            "default_capabilities": (recipe.get("role_definition", {}) or {}).get(
                "default_capabilities", []
            ),
            "allowed_tools": (recipe.get("role_definition", {}) or {}).get(
                "allowed_tools", []
            ),
        }],
        "skills": recipe.get("skills", []),
        "skill_catalog": recipe.get("skill_catalog", []),
        "capability_catalog": recipe.get("capability_catalog", []),
        "provider_registry": "schema/provider_registry.yaml",\n        "provider_registry_snapshot": {\n            "digest": registry_snapshot["digest"],\n            "artifact": "provider-registry.snapshot.json",\n        },
        "provider_interfaces": ["mcp", "api", "tool"],
        "capability_graph": [{
            "skill": skill.get("id"),
            "capabilities": skill.get("capabilities", []) or [],
            "tools": skill.get("tools", []) or [],
            "evidence_inputs": skill.get("evidence_inputs", []) or [],
            "evidence_outputs": skill.get("evidence_outputs", []) or [],
        } for skill in recipe.get("skills", [])],
        "experiment_graph": experiment_graph,
        "orchestration": recipe["environment"].get(
            "orchestration", {"executor": "codex", "mode": "interactive"}
        ),
        "capabilities": _required_capabilities(recipe, registry_path),
        "capability_requirements": _required_capabilities(recipe, registry_path),
        "resolution": resolution_audit,
        "execution_plan": execution_plan,
        "approval_plan": approval_plan,
        "plan_digest": plan_digest,
        "policy": recipe["policy"],
        "evidence": recipe["evidence"],
        "completion": recipe["completion"],
        "workload": recipe.get("workload", {}),
        "reports": recipe.get("reports", []),\n        "compilation_manifest": {"artifact": "compilation-manifest.json"},
    }

    compilation_manifest = create_manifest(Path(recipe.get("_source_path", "recipe.yaml")), schema_path, registry_path, artifact_dir) if Path(recipe.get("_source_path", "recipe.yaml")).exists() else None\n    if compilation_manifest:\n        body["compilation_manifest"] = {"artifact": "compilation-manifest.json", "digest": compilation_manifest["digest"]}\n    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
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
