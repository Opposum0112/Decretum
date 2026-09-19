"""Compile capability recipes into harness-neutral research execution contracts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .manifest import create_manifest
from .registry_snapshot import snapshot_registry
from .resolver import resolve_capabilities
from .validator import DEFAULT_PROVIDER_REGISTRY, required_capabilities


@dataclass(frozen=True, slots=True)
class ExecutionContract:
    contract_id: str
    contract: dict[str, Any]
    artifact_dir: Path


def _experiment_steps(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    steps = []
    for step in recipe.get("experiments", []) or []:
        capabilities = list(step.get("capabilities", []) or [])
        if step.get("capability"):
            capabilities.append(step["capability"])
        steps.append({
            "id": step["id"],
            "objective": step.get("objective"),
            "capabilities": sorted(set(capabilities)),
            "depends_on": sorted(step.get("depends_on", []) or []),
            "inputs": sorted(step.get("inputs", []) or []),
            "outputs": sorted(step.get("outputs", []) or []),
            "approval_required": bool(step.get("approval_required", False)),
        })
    return steps


def _plan_digest(plan: dict[str, Any]) -> str:
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def compile_recipe(recipe: dict[str, Any], artifact_dir: Path, registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> ExecutionContract:
    registry_snapshot = snapshot_registry(registry_path, artifact_dir)
    schema_path = Path(__file__).resolve().parent.parent / "schema" / "sec_research_metamodel.yaml"
    resolution = resolve_capabilities(recipe, registry_path)
    steps = _experiment_steps(recipe)
    experiment_graph = {
        "steps": steps,
        "entrypoints": [s["id"] for s in steps if not s["depends_on"]],
        "execution_order": [s["id"] for s in steps],
    }
    execution_plan = resolution.get("experiment_plan", [])
    approval_plan = {
        "required": sorted({c for step in execution_plan for c in step.get("approval_required", [])}),
        "steps": [step["id"] for step in execution_plan if step.get("approval_required")],
    }
    resolution_audit = {
        "status": resolution.get("status"),
        "capabilities": resolution.get("capabilities", []),
        "failures": resolution.get("failures", []),
        "harnesses": resolution.get("harnesses", []),
        "harness_requirements": resolution.get("harness_requirements", []),
        "harness_checks": resolution.get("harness_checks", {}),
        "provider_preferences": resolution.get("provider_preferences", {}),
        "readiness": resolution.get("readiness", {}),
        "execution_surfaces": resolution.get("execution_surfaces", []),
        "experiment_plan": execution_plan,
    }
    plan_digest = _plan_digest(resolution_audit)
    harness = ((recipe.get("environment") or {}).get("orchestration") or {}).get("executor", "codex")
    instrumentation = recipe.get("instrumentation") or {}
    compute = recipe.get("compute") or {}
    requirements = {
        "instrumentation": {
            "required": sorted(instrumentation.get("required", []) or []) if isinstance(instrumentation, dict) else [],
            "preferred": sorted(instrumentation.get("preferred", []) or []) if isinstance(instrumentation, dict) else [],
        },
        "compute": {
            "required": sorted(compute.get("required", []) or []) if isinstance(compute, dict) else [],
            "preferred": sorted(compute.get("preferred", []) or []) if isinstance(compute, dict) else [],
        },
    }
    body: dict[str, Any] = {
        "apiVersion": "decretum.dev/v1",
        "kind": "ResearchExecutionContract",
        "contract_version": "3",
        "contract_id": "",
        "research": {"id": recipe["id"], "name": recipe["name"], "version": recipe["version"], "objective": recipe["objective"]},
        "capabilities": sorted(required_capabilities(recipe, registry_path)),
        "requirements": requirements,
        "experiment_graph": experiment_graph,
        "execution": {
            "harness": harness,
            "resolution": resolution_audit,
            "approval_plan": approval_plan,
            "policy": recipe.get("policy", {}),
            "orchestration": (recipe.get("environment") or {}).get("orchestration", {"executor": harness, "mode": "interactive"}),
        },
        "research_loop": {
            "interactive": True,
            "persist_evidence": True,
            "persist_findings": True,
            "persist_report": True,
            "harness_responsible_for": ["provision", "implement_capabilities", "execute", "orchestrate", "collect_evidence", "researcher_interaction"],
        },
        "evidence": recipe.get("evidence", {}),
        "completion": recipe.get("completion", {}),
        "reports": recipe.get("reports", []),
        "provider_registry_snapshot": {"digest": registry_snapshot["digest"], "artifact": "provider-registry.snapshot.json"},
        "plan_digest": plan_digest,
        "compilation_manifest": {"artifact": "compilation-manifest.json"},
    }
    source = Path(recipe.get("_source_path", "recipe.yaml"))
    manifest = create_manifest(source, schema_path, registry_path, artifact_dir) if source.exists() else None
    if manifest:
        body["compilation_manifest"] = {"artifact": "compilation-manifest.json", "digest": manifest["digest"]}
    canonical = json.dumps({k:v for k,v in body.items() if k != "contract_id"}, sort_keys=True, separators=(",", ":")).encode()
    contract_id = hashlib.sha256(canonical).hexdigest()[:16]
    body["contract_id"] = contract_id
    return ExecutionContract(contract_id, body, artifact_dir)


def write_contract(contract: ExecutionContract) -> Path:
    contract.artifact_dir.mkdir(parents=True, exist_ok=True)
    path = contract.artifact_dir / "research-contract.json"
    path.write_text(json.dumps(contract.contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
