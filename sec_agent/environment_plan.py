"""Schema-shaped environment and provisioning planning."""
from __future__ import annotations
from typing import Any

def plan_environment(recipe: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    env = recipe.get("environment", {}) or {}
    compute = env.get("compute", {}) or {}
    sandbox = env.get("sandbox", {}) or {}
    provider_id = compute.get("provider") or sandbox.get("backend")
    provider = (registry.get("providers", {}) or {}).get(provider_id, {}) if provider_id else {}
    provisioning = provider.get("provisioning", {}) or {}
    lifecycle = provider.get("lifecycle", {}) or {}
    ready = bool(provider_id and provider)
    installation_required = bool(provider_id and provisioning.get("installable") and not ready)
    # Discovery/readiness is intentionally separated from this pure plan. A missing
    # executable is represented by the caller as unavailable; no host mutation occurs here.
    return {
        "provider": provider_id,
        "compute": compute,
        "sandbox": sandbox,
        "provisioning": {
            "provider": provider_id,
            "status": "registered" if ready else "unavailable",
            "prerequisites": [provisioning.get("executable")] if provisioning.get("executable") else [],
            "installation_required": installation_required,
            "approval_required": bool(provisioning.get("approval_required", True)) if installation_required else False,
            "actions": ([provisioning.get("installer")] if provisioning.get("installer") else []),
        },
        "isolation": provider.get("isolation") or sandbox.get("backend"),
        "network": provider.get("network") or compute.get("network"),
        "ephemeral": bool(compute.get("ephemeral", True)),
        "lifecycle": lifecycle,
    }
