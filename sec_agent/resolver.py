"""Resolve recipe capabilities to concrete providers and compatible execution interfaces."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil

from .validator import (
    DEFAULT_PROVIDER_REGISTRY,
    load_provider_registry,
    provider_capability_index,
    registry_errors,
)


def _required(recipe: dict[str, Any]) -> set[str]:
    required = set()
    for cap in recipe.get("capability_catalog", []) or []:
        if isinstance(cap, dict) and cap.get("id"):
            required.add(cap["id"])
    for skill in recipe.get("skills", []) or []:
        if isinstance(skill, dict):
            required.update(skill.get("capabilities", []) or [])
    role = recipe.get("role_definition") or {}
    required.update(role.get("default_capabilities", []) or [])
    workload = recipe.get("workload") or {}
    if workload.get("command"):
        required.add("process.execute")
    for step in recipe.get("experiments", []) or []:
        required.update(step.get("capabilities", []) or [])
        if step.get("capability"):
            required.add(step["capability"])
    return required


def _provider_available(interface: dict[str, Any]) -> bool:
    if interface.get("type") != "tool":
        return True
    executable = interface.get("executable")
    return not executable or shutil.which(executable) is not None


def resolve_capabilities(
    recipe: dict[str, Any],
    registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
) -> dict[str, Any]:
    errors = registry_errors(registry_path)
    if errors:
        return {"status": "invalid_registry", "errors": errors, "capabilities": []}

    registry = load_provider_registry(str(registry_path))
    providers = registry.get("providers", {}) or {}
    integrations = registry.get("integrations", {}) or {}
    harnesses = registry.get("harnesses", {}) or {}
    models = registry.get("models", {}) or {}
    index = provider_capability_index(registry)

    requested_harness = (recipe.get("environment") or {}).get("orchestration", {}).get("executor")
    harness_candidates = (
        [requested_harness] if requested_harness and requested_harness in harnesses
        else sorted(harnesses)
    )

    capabilities = []
    for cap in sorted(_required(recipe)):
        candidates = []
        for pid in index.get(cap, []):
            provider = providers[pid]
            interface = provider.get("interface", {}) or {}
            available = _provider_available(interface)
            supported = [
                h for h in harness_candidates
                if interface.get("type") in (harnesses.get(h, {}).get("supported_interfaces", []) or [])
            ]
            candidates.append({
                "provider": pid,
                "interface": interface.get("type"),
                "available": available,
                "harnesses": supported,
                "integrations": provider.get("integrations", []) or [],
            })
        ready = [
            c for c in candidates
            if c["available"] and c["harnesses"]
        ]
        capabilities.append({
            "capability": cap,
            "status": "ready" if ready else ("registered" if candidates else "unavailable"),
            "providers": candidates,
        })

    status = "ready" if all(c["status"] == "ready" for c in capabilities) else "needs_prerequisites"
    return {
        "status": status,
        "capabilities": capabilities,
        "harnesses": harness_candidates,
        "integrations": sorted(integrations),
        "models": sorted(models),
    }
