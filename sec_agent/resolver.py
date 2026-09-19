"""Resolve capabilities into deterministic provider/harness execution plans."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .readiness import assess_readiness
from .validator import DEFAULT_PROVIDER_REGISTRY, load_provider_registry, provider_capability_index, registry_errors


def _required(recipe: dict[str, Any]) -> set[str]:
    required = {"artifact.read", "artifact.collect"}
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


def _candidate_rank(candidate: dict[str, Any]) -> tuple[int, int, str]:
    """Prefer ready local/tool paths, then ready API/MCP paths, deterministically."""
    interface = candidate.get("interface")
    interface_rank = {"tool": 0, "api": 1, "mcp": 2}.get(interface, 9)
    return (0 if candidate.get("ready") else 1, interface_rank, candidate["provider"])


def _resolve_step(step: dict[str, Any], capability_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    capabilities = list(step.get("capabilities", []) or [])
    if step.get("capability"):
        capabilities.append(step["capability"])
    bindings = []
    failures = []
    for capability in sorted(set(capabilities)):
        item = capability_map.get(capability)
        if not item:
            failures.append({"capability": capability, "reason": "not registered"})
            continue
        ready = [p for p in item["providers"] if p.get("ready")]
        if not ready:
            failures.append({
                "capability": capability,
                "reason": "no ready provider",
                "providers": item["providers"],
            })
            continue
        selected = sorted(ready, key=_candidate_rank)[0]
        bindings.append({
            "capability": capability,
            "provider": selected["provider"],
            "interface": selected["interface"],
            "harnesses": selected["harnesses"],
            "integrations": selected["integrations"],
            "fallbacks": [
                {
                    "provider": p["provider"],
                    "interface": p["interface"],
                    "harnesses": p["harnesses"],
                }
                for p in sorted(ready, key=_candidate_rank)[1:]
            ],
        })
    return {
        "id": step["id"],
        "depends_on": list(step.get("depends_on", []) or []),
        "bindings": bindings,
        "failures": failures,
        "ready": not failures,
    }


def resolve_capabilities(recipe: dict[str, Any], registry_path: Path = DEFAULT_PROVIDER_REGISTRY) -> dict[str, Any]:
    errors = registry_errors(registry_path)
    if errors:
        return {"status": "invalid_registry", "errors": errors, "capabilities": []}

    registry = load_provider_registry(str(registry_path))
    readiness = assess_readiness(registry)
    providers = registry.get("providers", {}) or {}
    harnesses = registry.get("harnesses", {}) or {}
    integrations = registry.get("integrations", {}) or {}
    models = registry.get("models", {}) or {}
    index = provider_capability_index(registry)

    requested_harness = (recipe.get("environment") or {}).get("orchestration", {}).get("executor")
    harness_candidates = (
        [requested_harness] if requested_harness in harnesses
        else sorted(harnesses)
    )

    capabilities = []
    capability_map = {}
    for cap in sorted(_required(recipe)):
        candidates = []
        for pid in index.get(cap, []):
            provider = providers[pid]
            interface = provider.get("interface", {}) or {}
            readiness_item = readiness["providers"].get(pid, {})
            ready = bool(readiness_item.get("ready"))
            supported = [
                h for h in harness_candidates
                if interface.get("type") in (harnesses.get(h, {}).get("supported_interfaces", []) or [])
            ]
            candidates.append({
                "provider": pid,
                "interface": interface.get("type"),
                "ready": ready and bool(supported),
                "provider_ready": ready,
                "harnesses": supported,
                "integrations": provider.get("integrations", []) or [],
                "readiness": readiness_item.get("checks", []),
            })
        item = {
            "capability": cap,
            "status": "ready" if any(p["ready"] for p in candidates) else ("registered" if candidates else "unavailable"),
            "providers": candidates,
        }
        capabilities.append(item)
        capability_map[cap] = item

    steps = [_resolve_step(step, capability_map) for step in recipe.get("experiments", []) or []]
    global_failures = [
        {"capability": item["capability"], "reason": "no ready provider"}
        for item in capabilities if item["status"] != "ready"
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
        "integrations": sorted(integrations),
        "models": sorted(models),
        "readiness": readiness,
    }
