"""Verify compiled contracts without executing them."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .compiler import _plan_digest
from .registry_snapshot import load_snapshot
from .validator import DEFAULT_PROVIDER_REGISTRY, load_provider_registry


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contract_plan(contract: dict[str, Any]) -> dict[str, Any]:
    resolution = contract.get("execution", {}).get("resolution", {})
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
    return {"valid": bool(expected) and expected == actual, "expected": expected, "actual": actual}


def current_environment(registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    registry = load_provider_registry(str(registry_path))
    return {
        "registry_digest": hashlib.sha256(
            json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }


def replay_contract(contract_path: Path, registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    """Perform read-only contract integrity checks. No tools, harnesses or agents are started."""
    contract = load_contract(contract_path)
    digest = verify_plan_digest(contract)
    snapshot_path = contract_path.parent / "provider-registry.snapshot.json"
    snapshot_valid = False
    snapshot_digest = None
    if snapshot_path.exists():
        try:
            snapshot = load_snapshot(snapshot_path)
            snapshot_digest = snapshot["digest"]
            snapshot_valid = snapshot_digest == contract.get("provider_registry_snapshot", {}).get("digest")
        except (ValueError, KeyError, json.JSONDecodeError):
            snapshot_valid = False
    current = current_environment(registry_path)
    return {
        "contract_id": contract.get("contract_id"),
        "plan_digest": contract.get("plan_digest"),
        "plan_integrity": digest,
        "registry_snapshot": {
            "present": snapshot_path.exists(),
            "valid": snapshot_valid,
            "digest": snapshot_digest,
        },
        "current_registry_digest": current["registry_digest"],
        "replayable": digest["valid"] and snapshot_valid,
        "execution": "not_run",
    }
