"""Resolve capabilities into deterministic provider/harness execution plans."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .capability_discovery import discover_capability_surfaces
from .compatibility import compatibility
from .policy import annotate_provider, plan_step
from .readiness import assess_readiness
from .validator import (
    DEFAULT_PROVIDER_REGISTRY,
    load_provider_registry,
    provider_capability_index,
    registry_errors,
)


def _required(recipe: dict[str, Any]) -> set[str]:
    required = {"artifact.read", "artifact.collect"}
    instrumentation = recipe.get("instrumentation") or {}
    compute = recipe.get("compute") or {}
    if isinstance(instrumentation, dict):
        required.update(instrumentation.get("required", []) or [])
    if isinstance(compute, dict):
        required.update(compute.get("required", []) or [])
    for cap in recipe.get("capability_catalog", []) or []:
        if isinstance(cap, dict) and cap.get("id"):
            required.add(cap["id"])
    for skill in recipe.get("skills", []) or []:
        if isinstance(skill, dict):
            required.update(skill.get("capabilities", []) or [])
    required.update((recipe.get("role_definition") or {}).get("default_capabilities", []) or [])
    if (recipe.get("workload") or {}).get("command"):
        required.add("process.execute")
    for step in recipe.get("experiments", []) or []:
        required.update(step.get("capabilities", []) or [])
        if step.get("capability"):
            required.add(step["capability"])
    return required


def _candidate_rank(candidate: dict[str, Any]) -> tuple[int, int, int, str]:
    """Prefer preferred providers, then ready local/tool paths, deterministically."""
    interface_rank = {"tool": 0, "api": 1, "mcp": 2}.get(candidate.get("interface"), 9)
    return (0 if candidate.get("preferred") else 1, 0 if candidate.get("ready") else 1, interface_rank, candidate["provider"])


def resolve_capabilities(
    recipe: dict[str, Any],
    registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
) -> dict[str, Any]:
    """Resolve registered capabilities and verify their host execution surfaces."""
    errors = registry_errors(registry_path)
    if errors:
        return {"status": "invalid_registry", "errors": errors, "capabilities": []}

    registry = load_provider_registry(str(registry_path))
    readiness = assess_readiness(registry)
    surface_report = discover_capability_surfaces(registry_path, recipe)
    surface_index = {
        (item["capability"], item["provider"], item["interface"]): item
        for item in surface_report.get("surfaces", [])
    }

    providers = registry.get("providers", {}) or {}
    harnesses = registry.get("harnesses", {}) or {}
    integrations = registry.get("integrations", {}) or {}
    models = registry.get("models", {}) or {}
    index = provider_capability_index(registry)

    requested_harness = (recipe.get("environment") or {}).get("orchestration", {}).get("executor")
    harness_candidates = (
        [requested_harness] if requested_harness in harnesses else sorted(harnesses)
    )
    instrumentation = recipe.get("instrumentation") or {}
    compute = recipe.get("compute") or {}
    preferred_providers = set()
    if isinstance(instrumentation, dict):
        preferred_providers.update(instrumentation.get("preferred", []) or [])
    if isinstance(compute, dict):
        preferred_providers.update(compute.get("preferred", []) or [])
    specs = {
        item["id"]: item
        for item in (recipe.get("capability_catalog", []) or [])
        if isinstance(item, dict) and item.get("id")
    }

    capabilities = []
    capability_map: dict[str, dict[str, Any]] = {}

    for cap in sorted(_required(recipe)):
        candidates = []
        for pid in index.get(cap, []):
            provider = providers[pid]
            interface = provider.get("interface", {}) or {}
            interface_type = interface.get("type")
            readiness_item = readiness["providers"].get(pid, {})
            provider_ready = bool(readiness_item.get("ready"))
            supported = [
                h for h in harness_candidates
                if interface_type in (harnesses.get(h, {}).get("supported_interfaces", []) or [])
            ]
            surface = surface_index.get((cap, pid, interface_type))
            surface_ready = bool(surface and surface.get("ready"))
            annotated = annotate_provider(provider, cap, recipe, specs)
            compat = compatibility(provider, cap, specs.get(cap, {}))
            candidate = {
                "provider": pid,
                "interface": interface_type,
                "preferred": pid in preferred_providers,
                "ready": provider_ready and bool(supported) and surface_ready and compat["compatible"],
                "provider_ready": provider_ready,
                "harnesses": supported,
                "integrations": provider.get("integrations", []) or [],
                "readiness": readiness_item.get("checks", []),
                "execution_surface": surface,
                "execution_surface_ready": surface_ready,
                "compatibility": compat,
                "policy_compatible": annotated["policy_compatible"],
                "policy": annotated["policy"],
            }
            candidates.append(candidate)

        status = (
            "ready"
            if any(p["ready"] and p["policy_compatible"] for p in candidates)
            else ("registered" if candidates else "unavailable")
        )
        item = {"capability": cap, "status": status, "providers": candidates}
        capabilities.append(item)
        capability_map[cap] = item

    steps = [
        plan_step(step, capability_map, recipe, specs)
        for step in recipe.get("experiments", []) or []
    ]
    global_failures = [
        {"capability": item["capability"], "reason": "no ready execution surface"}
        for item in capabilities
        if item["status"] != "ready"
    ]
    status = "ready" if not global_failures and all(s["ready"] for s in steps) else "needs_prerequisites"

    return {
        "status": status,
        "capabilities": capabilities,
        "experiment_plan": steps,
        "failures": global_failures + [
            {"experiment": s["id"], "failures": s["failures"]}
            for s in steps if s["failures"]
        ],
        "harnesses": harness_candidates,
        "provider_preferences": {
            "instrumentation": (instrumentation.get("preferred", []) or []) if isinstance(instrumentation, dict) else [],
            "compute": (compute.get("preferred", []) or []) if isinstance(compute, dict) else [],
        },
        "integrations": sorted(integrations),
        "models": sorted(models),
        "readiness": readiness,
        "execution_surfaces": surface_report,
    }
