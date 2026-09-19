"""Reconstruct and compare Decretum research execution plans."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .compiler import _plan_digest
from .readiness import assess_readiness
from .validator import DEFAULT_PROVIDER_REGISTRY, load_provider_registry


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_plan(contract: dict[str, Any]) -> dict[str, Any]:
    resolution = contract.get("resolution", {})
    return {
        "status": resolution.get("status"),
        "capabilities": resolution.get("capabilities", []),
        "failures": resolution.get("failures", []),
        "harnesses": resolution.get("harnesses", []),
        "readiness": resolution.get("readiness", {}),
        "experiment_plan": resolution.get("experiment_plan", []),
    }


def verify_plan_digest(contract: dict[str, Any]) -> dict[str, Any]:
    plan = contract_plan(contract)
    expected = contract.get("plan_digest", "")
    actual = _plan_digest(plan)
    return {
        "valid": bool(expected) and expected == actual,
        "expected": expected,
        "actual": actual,
    }


def current_environment(registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    registry = load_provider_registry(str(registry_path))
    return {
        "readiness": assess_readiness(registry),
        "registry_digest": hashlib.sha256(
            json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def compare_environment(contract: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    current = current_environment(registry_path)
    recorded = contract.get("resolution", {}).get("readiness", {})
    differences = []

    if recorded != current["readiness"]:
        differences.append({
            "type": "readiness_changed",
            "recorded": recorded,
            "current": current["readiness"],
        })

    return {
        "reproducible": not differences and verify_plan_digest(contract)["valid"],
        "differences": differences,
        "current_registry_digest": current["registry_digest"],
    }


def replay_contract(contract_path: Path, registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    contract = load_contract(contract_path)
    digest = verify_plan_digest(contract)
    environment = compare_environment(contract, registry_path)
    return {
        "contract_id": contract.get("contract_id"),
        "plan_digest": contract.get("plan_digest"),
        "plan_integrity": digest,
        "environment": environment,
        "replayable": digest["valid"],
        "execution": "not_run",
    }
