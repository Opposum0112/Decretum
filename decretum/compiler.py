"""Compile capability recipes into harness-neutral execution contracts.

Decretum compiles and stops at the handoff boundary. It does not execute
execution workloads, run a harness, manage interaction, or persist state.
Those responsibilities belong to the external harness runtime and its external store.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import create_manifest
from .registry_snapshot import snapshot_registry
from .resolver import resolve_capabilities
from .validator import DEFAULT_PROVIDER_REGISTRY, required_capabilities, validate_execution_contract_schema


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    contract: dict[str, Any]
    artifact_dir: Path


def _experiment_steps(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for step in recipe.get("experiments", []) or []:
        capabilities = list(step.get("capabilities", []) or [])
        if step.get("capability"):
            capabilities.append(step["capability"])
        result.append({
            "id": step["id"],
            "objective": step.get("objective"),
            "capabilities": sorted(set(capabilities)),
            "depends_on": sorted(step.get("depends_on", []) or []),
            "inputs": sorted(step.get("inputs", []) or []),
            "outputs": sorted(step.get("outputs", []) or []),
            "approval_required": bool(step.get("approval_required", False)),
        })
    return result


def _plan_digest(plan: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def compile_recipe(
    recipe: dict[str, Any],
    artifact_dir: Path,
    registry_path: Path | None = DEFAULT_PROVIDER_REGISTRY,
) -> ExecutionContract:
    """Resolve a recipe and produce a portable contract for an external harness runtime."""
    if registry_path is None:\n        from .domain_packs import resource_for_domain\n        registry_path = resource_for_domain(recipe.get("domain"), "providers") / "provider_registry.yaml"\n    registry_snapshot = snapshot_registry(registry_path, artifact_dir)
    schema_path = None
    resolution = resolve_capabilities(recipe, registry_path)
    recipe_canonical = {k: v for k, v in recipe.items() if not k.startswith("_")}
    recipe_digest = hashlib.sha256(json.dumps(recipe_canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    steps = _experiment_steps(recipe)
    experiment_graph = {
        "steps": steps,
        "entrypoints": [s["id"] for s in steps if not s["depends_on"]],
        "execution_order": [s["id"] for s in steps],
    }
    if resolution.get("status") != "ready":
        raise ValueError("recipe cannot be compiled: capability resolution is not ready")

    execution_plan = resolution.get("experiment_plan", [])
    resolution_audit = {
        "status": resolution.get("status"),
        "capabilities": resolution.get("capabilities", []),
        "failures": resolution.get("failures", []),
        "profiles": resolution.get("profiles", {}),
        "harnesses": resolution.get("harnesses", []),
        "harness_requirements": resolution.get("harness_requirements", []),
        "harness_checks": resolution.get("harness_checks", {}),
        "provider_preferences": resolution.get("provider_preferences", {}),
        "readiness": resolution.get("readiness", {}),
        "execution_surfaces": resolution.get("execution_surfaces", []),
        "experiment_plan": execution_plan,
    }
    harnesses = resolution.get("profiles", {}).get("harness", {}).get("preferred", [])
    harness = harnesses[0] if harnesses else "codex"

    body: dict[str, Any] = {
        "apiVersion": "decretum.dev/v1",
        "kind": "ExecutionContract",
        "domain": recipe.get("domain", "general"),
        "intent": {
            "id": recipe["id"],
            "name": recipe["name"],
            "objective": recipe["objective"],
        },
        "contract_version": "5",
        "contract_id": "",
        "capabilities": sorted(required_capabilities(recipe, registry_path)),
        "capability_plan": resolution.get("capability_plan", []),
        "recipe_digest": recipe_digest,
        "spec_source": recipe.get("_spec_source", {}),
        "profiles": resolution.get("profiles", {}),
        "experiment_graph": experiment_graph,
        "execution": {
            "harness": harness,
            "resolution": resolution_audit,
            "approval_plan": {
                "required": sorted({
                    c for step in execution_plan for c in step.get("approval_required", [])
                }),
                "steps": [step["id"] for step in execution_plan if step.get("approval_required")],
            },
            "policy": recipe.get("policy", {}),
            "orchestration": {"mode": "interactive", "executor": harness},
        },
        "handoff": {
            "target": "external_harness_runtime",
            "mode": "contract_only",
            "decretum_stops_after_compilation": True,
            "runtime_owns": [
                "interaction",
                "environment_provisioning",
                "capability_implementation",
                "execution",
                "orchestration",
                "evidence_collection",
                "result_persistence",
            ],
            "runtime_must_not_change_contract_semantics": True,
            "new_capability_or_requirement": "return_to_decretum_for_resolution_and_recompilation",
        },
        "execution_loop": {
            "interactive": True,
            "owner": "external_harness_runtime",
        },
        "evidence": recipe.get("evidence", {}),
        "completion": recipe.get("completion", {}),
        "reports": recipe.get("reports", []),
        "provider_registry_snapshot": {
            "digest": registry_snapshot["digest"],
            "artifact": "provider-registry.snapshot.json",
        },
        "plan_digest": _plan_digest(resolution_audit),
        "compilation_manifest": {"artifact": "compilation-manifest.json"},
    }

    source = Path(recipe.get("_source_path", "recipe.yaml"))
    manifest = create_manifest(source, schema_path, registry_path, artifact_dir) if source.exists() and schema_path else None
    if manifest:
        body["compilation_manifest"] = {
            "artifact": "compilation-manifest.json",
            "digest": manifest["digest"],
        }

    canonical = json.dumps(
        {k: v for k, v in body.items() if k != "contract_id"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    body["contract_id"] = hashlib.sha256(canonical).hexdigest()[:16]
    schema_errors = validate_execution_contract_schema(body)
    if schema_errors:
        raise ValueError("compiled execution contract failed schema validation: " + "; ".join(schema_errors))
    return ExecutionContract(body["contract_id"], body, artifact_dir)


def write_contract(contract: ExecutionContract) -> Path:
    """Write only the compiled handoff artifact; never execute it."""
    contract.artifact_dir.mkdir(parents=True, exist_ok=True)
    path = contract.artifact_dir / "execution-contract.json"
    path.write_text(
        json.dumps(contract.contract, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
