"""Resolve capabilities into concrete provider/integration/harness execution surfaces."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .capability_discovery import discover_capability_surfaces
from .compatibility import compatibility
from .policy import annotate_provider, plan_step
from .profile_registry import DEFAULT_PROFILE_REGISTRY, resolve_recipe_profiles
from .readiness import assess_readiness
from .validator import DEFAULT_PROVIDER_REGISTRY, load_provider_registry, provider_capability_index, registry_errors


def _required(recipe: dict[str, Any]) -> set[str]:
    required = {"artifact.read", "artifact.collect"}
    required.update(recipe.get("capabilities", []) or [])
    for skill in recipe.get("skills", []) or []:
        if isinstance(skill, dict):
            required.update(skill.get("capabilities", []) or [])
    role = recipe.get("role_definition") or {}
    if isinstance(role, dict):
        required.update(role.get("default_capabilities", []) or [])
    if (recipe.get("workload") or {}).get("command"):
        required.add("process.execute")
    for step in recipe.get("experiments", []) or []:
        required.update(step.get("capabilities", []) or [])
        if step.get("capability"):
            required.add(step["capability"])
    return required


def _required_harness_operations(profile: dict[str, Any], infrastructure: dict[str, Any]) -> set[str]:
    operations = {"implement_capabilities", "execute", "orchestrate", "collect_evidence", "researcher_interaction"}
    compute = infrastructure.get("compute", {}) if isinstance(infrastructure, dict) else {}
    if isinstance(compute, dict) and compute.get("type") in {"vm", "container", "microvm"}:
        operations.add("provision")
    return operations


def _harness_compatibility(harness_id: str, harnesses: dict[str, Any], required: set[str]) -> dict[str, Any]:
    spec = harnesses.get(harness_id, {}) or {}
    available_ops = set(spec.get("operations", []) or [])
    missing = sorted(required - available_ops)
    return {"harness": harness_id, "compatible": not missing, "required_operations": sorted(required), "missing_operations": missing}


def resolve_capabilities(
    recipe: dict[str, Any],
    registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
    profile_path: Path = DEFAULT_PROFILE_REGISTRY,
) -> dict[str, Any]:
    """Resolve canonical capability semantics plus independent profile preferences."""
    errors = registry_errors(registry_path)
    if errors:
        return {"status": "invalid_registry", "errors": errors, "capabilities": []}

    registry = load_provider_registry(registry_path, recipe.get("domain"))
    profiles = resolve_recipe_profiles(recipe, profile_path)
    infrastructure = profiles["profiles"].get("infrastructure", {})
    instrumentation = profiles["profiles"].get("instrumentation", {})
    harness_profile = profiles["profiles"].get("harness", {})

    readiness = assess_readiness(registry)
    surface_report = discover_capability_surfaces(registry_path, recipe)
    surface_index = {(x["capability"], x["provider"], x["interface"]): x for x in surface_report.get("surfaces", [])}
    providers = registry.get("providers", {}) or {}
    harnesses = registry.get("harnesses", {}) or {}
    integrations = registry.get("integrations", {}) or {}
    models = registry.get("models", {}) or {}
    index = provider_capability_index(registry)

    requested_harness = None
    preferred_harnesses = harness_profile.get("preferred", []) if isinstance(harness_profile, dict) else []
    if requested_harness in harnesses:
        harness_candidates = [requested_harness]
    elif preferred_harnesses:
        harness_candidates = [h for h in preferred_harnesses if h in harnesses] + [h for h in sorted(harnesses) if h not in preferred_harnesses]
    else:
        harness_candidates = sorted(harnesses)

    required_harness_operations = _required_harness_operations(harness_profile, infrastructure)
    harness_checks = {h: _harness_compatibility(h, harnesses, required_harness_operations) for h in harness_candidates}
    harness_candidates = [h for h in harness_candidates if harness_checks[h]["compatible"]]

    preferred_providers = set()
    preferred_providers.update(instrumentation.get("preferred_providers", []) if isinstance(instrumentation, dict) else [])
    compute = infrastructure.get("compute", {}) if isinstance(infrastructure, dict) else {}
    if isinstance(compute, dict):
        preferred_providers.update(compute.get("preferred_providers", []) or [])

    capabilities = []
    capability_map: dict[str, dict[str, Any]] = {}
    for cap in sorted(_required(recipe)):
        candidates = []
        for pid in index.get(cap, []):
            provider = providers[pid]
            interface_type = (provider.get("interface", {}) or {}).get("type")
            readiness_item = readiness["providers"].get(pid, {})
            provider_ready = bool(readiness_item.get("ready"))
            supported = [h for h in harness_candidates if interface_type in (harnesses.get(h, {}).get("supported_interfaces", []) or [])]
            surface = surface_index.get((cap, pid, interface_type))
            surface_ready = bool(surface and surface.get("ready"))
            annotated = annotate_provider(provider, cap, recipe, {})
            compat = compatibility(provider, cap, {})
            candidates.append({
                "provider": pid,
                "interface": interface_type,
                "preferred": pid in preferred_providers,
                "ready": provider_ready and bool(supported) and surface_ready and compat["compatible"],
                "provider_ready": provider_ready,
                "harnesses": supported,
                "harness_compatibility": {h: harness_checks[h] for h in supported},
                "integrations": provider.get("integrations", []) or [],
                "readiness": readiness_item.get("checks", []),
                "execution_surface": surface,
                "execution_surface_ready": surface_ready,
                "invocation": {
                    "interface": interface_type,
                    "transport": provider.get("interface", {}),
                    "execution_modes": provider.get("execution_modes", []) or [],
                },
                "compatibility": compat,
                "policy_compatible": annotated["policy_compatible"],
                "policy": annotated["policy"],
            })
        status = "ready" if any(p["ready"] and p["policy_compatible"] for p in candidates) else ("registered" if candidates else "unavailable")
        ready_candidates = [
            p for p in candidates
            if p["ready"] and p["policy_compatible"]
        ]
        ready_candidates.sort(key=lambda p: (not p["preferred"], p["provider"], p["interface"]))
        selected = ready_candidates[0] if ready_candidates else None
        item = {
            "capability": cap,
            "status": status,
            "providers": candidates,
            "selected": selected,
        }
        capabilities.append(item)
        capability_map[cap] = item

    steps = [plan_step(step, capability_map, recipe, {}) for step in recipe.get("experiments", []) or []]
    failures = [{"capability": x["capability"], "reason": "no ready execution surface"} for x in capabilities if x["status"] != "ready"]
    failures += [{"experiment": s["id"], "failures": s["failures"]} for s in steps if s["failures"]]

    return {
        "status": "ready" if not failures and all(s["ready"] for s in steps) else "needs_prerequisites",
        "capabilities": capabilities,
        "capability_plan": [
            {
                "capability": item["capability"],
                "status": item["status"],
                "provider": (item["selected"] or {}).get("provider"),
                "interface": (item["selected"] or {}).get("interface"),
                "harnesses": (item["selected"] or {}).get("harnesses", []),
                "invocation": (item["selected"] or {}).get("invocation", {}),
                "integrations": (item["selected"] or {}).get("integrations", []),
            }
            for item in capabilities
        ],
        "experiment_plan": steps,
        "failures": failures,
        "profiles": {
            "references": profiles["references"],
            "infrastructure": infrastructure,
            "instrumentation": instrumentation,
            "harness": harness_profile,
        },
        "harnesses": harness_candidates,
        "harness_requirements": sorted(required_harness_operations),
        "harness_checks": harness_checks,
        "provider_preferences": {
            "instrumentation": sorted(instrumentation.get("preferred_providers", []) or []) if isinstance(instrumentation, dict) else [],
            "compute": sorted(compute.get("preferred_providers", []) or []) if isinstance(compute, dict) else [],
        },
        "integrations": sorted(integrations),
        "models": sorted(models),
        "readiness": readiness,
        "execution_surfaces": surface_report,
    }
