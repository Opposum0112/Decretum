"""Policy-aware provider planning."""
from __future__ import annotations

from typing import Any


def _capability_specs(recipe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["id"]: item
        for item in (recipe.get("capability_catalog", []) or [])
        if isinstance(item, dict) and item.get("id")
    }


def _risk_rank(risk: str | None) -> int:
    return {
        "read": 0, "observe": 1, "collect": 2, "network_access": 3,
        "write": 4, "execute": 5, "privileged": 6,
    }.get(risk or "execute", 99)


def policy_for_capability(
    capability: str,
    recipe: dict[str, Any],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    policy = recipe.get("policy", {}) or {}
    spec = specs.get(capability, {})
    denied = capability in set(policy.get("deny", []) or [])
    approval = (
        capability in set(policy.get("approval_required", []) or [])
        or bool(spec.get("requires_approval", False))
    )
    return {
        "denied": denied,
        "approval_required": approval,
        "risk": spec.get("risk"),
        "risk_rank": _risk_rank(spec.get("risk")),
    }


def annotate_provider(
    provider: dict[str, Any],
    capability: str,
    recipe: dict[str, Any],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    policy = policy_for_capability(capability, recipe, specs)
    provider_risk = provider.get("risk") or provider.get("risk_level")
    return {
        **provider,
        "policy": policy,
        "provider_risk": provider_risk,
        "semantics": {"isolation": provider.get("isolation", "unspecified"), "network": provider.get("network", "unspecified"), "privileged": bool(provider.get("privileged", False)), "evidence_outputs": sorted(provider.get("evidence_outputs", []) or []), "execution_modes": sorted(provider.get("execution_modes", []) or [])},
        "policy_compatible": not policy["denied"],
    }


def plan_step(
    step: dict[str, Any],
    capability_map: dict[str, dict[str, Any]],
    recipe: dict[str, Any],
    specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    bindings = []
    failures = []
    approvals = []
    for capability in sorted(set(
        list(step.get("capabilities", []) or [])
        + ([step["capability"]] if step.get("capability") else [])
    )):
        item = capability_map.get(capability)
        policy = policy_for_capability(capability, recipe, specs)
        if policy["denied"]:
            failures.append({"capability": capability, "reason": "denied_by_policy"})
            continue
        if not item:
            failures.append({"capability": capability, "reason": "not_registered"})
            continue
        ready = [p for p in item["providers"] if p.get("ready") and p.get("policy_compatible", True)]
        if not ready:
            failures.append({"capability": capability, "reason": "no_policy_compatible_ready_provider"})
            continue
        ordered = sorted(
            ready,
            key=lambda p: (
                0 if p.get("preferred") else 1,
                p.get("policy", {}).get("risk_rank", 99),
                {"tool": 0, "api": 1, "mcp": 2}.get(p.get("interface"), 9),
                p["provider"],
            ),
        )
        selected = ordered[0]
        binding = {
            "capability": capability,
            "provider": selected["provider"],
            "interface": selected["interface"],
            "harnesses": selected["harnesses"],
            "integrations": selected["integrations"],
            "policy": policy,
            "approval_required": bool(policy["approval_required"] or step.get("approval_required", False)),
            "fallbacks": [
                {"provider": p["provider"], "interface": p["interface"], "harnesses": p["harnesses"]}
                for p in ordered[1:]
            ],
        }
        bindings.append(binding)
        if binding["approval_required"]:
            approvals.append(capability)
    return {
        "id": step["id"],
        "depends_on": list(step.get("depends_on", []) or []),
        "bindings": bindings,
        "failures": failures,
        "approval_required": sorted(set(approvals)),
        "ready": not failures,
    }
