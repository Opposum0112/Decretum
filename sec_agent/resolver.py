"""Resolve recipe capabilities to usable providers, integrations, harnesses and models."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import shutil
from .validator import DEFAULT_PROVIDER_REGISTRY, load_provider_registry, registry_errors, provider_capability_index

def resolve_capabilities(recipe: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    errors = registry_errors(registry_path)
    if errors:
        return {"status":"invalid_registry","errors":errors,"capabilities":[]}
    registry = load_provider_registry(str(registry_path))
    providers = registry.get("providers", {}) or {}
    integrations = registry.get("integrations", {}) or {}
    harnesses = registry.get("harnesses", {}) or {}
    models = registry.get("models", {}) or {}
    index = provider_capability_index(registry)
    required = set()
    for cap in recipe.get("capability_catalog", []) or []:
        if isinstance(cap, dict) and cap.get("id"): required.add(cap["id"])
    for skill in recipe.get("skills", []) or []:
        if isinstance(skill, dict): required.update(skill.get("capabilities", []) or [])
    role = recipe.get("role_definition") or {}
    required.update(role.get("default_capabilities", []) or [])
    out=[]
    for cap in sorted(required):
        candidates=[]
        for pid in index.get(cap, []):
            p=providers[pid]
            interface=p.get("interface", {})
            executable=interface.get("executable")
            available = True if interface.get("type") != "tool" or not executable else shutil.which(executable) is not None
            candidates.append({"provider":pid,"interface":interface.get("type"),"available":available})
        out.append({"capability":cap,"status":"ready" if any(x["available"] for x in candidates) else ("registered" if candidates else "unavailable"),"providers":candidates})
    return {
        "status":"ready" if all(x["status"]=="ready" for x in out) else "needs_prerequisites",
        "capabilities":out,
        "harnesses":sorted(harnesses),
        "integrations":sorted(integrations),
        "models":sorted(models),
    }
