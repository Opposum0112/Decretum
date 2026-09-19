"""Schema-governed compatibility checks for provider substitution."""
from __future__ import annotations

from typing import Any


ISOLATIONS = {"unspecified", "host", "container", "vm", "sandbox"}
NETWORK_MODES = {"unspecified", "none", "restricted", "host", "internet"}
EXECUTION_MODES = {"capture", "observe", "analyze", "execute", "collect", "write"}


def semantics_from_capability(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "risk": spec.get("risk"),
        "requires_approval": bool(spec.get("requires_approval", False)),
        "evidence_outputs": sorted(spec.get("evidence_outputs", []) or []),
        "allowed_isolations": sorted(spec.get("allowed_isolations", []) or []),
        "allowed_networks": sorted(spec.get("allowed_networks", []) or []),
        "allowed_execution_modes": sorted(spec.get("allowed_execution_modes", []) or []),
    }


def validate_semantics(semantics: dict[str, Any]) -> list[str]:
    errors = []
    if semantics.get("isolation") not in ISOLATIONS:
        errors.append(f"unsupported isolation: {semantics.get('isolation')!r}")
    if semantics.get("network") not in NETWORK_MODES:
        errors.append(f"unsupported network mode: {semantics.get('network')!r}")
    for mode in semantics.get("execution_modes", []) or []:
        if mode not in EXECUTION_MODES:
            errors.append(f"unsupported execution mode: {mode!r}")
    return errors


def compatibility(
    provider: dict[str, Any],
    capability: str,
    capability_spec: dict[str, Any],
) -> dict[str, Any]:
    interface = provider.get("interface", {}) or {}
    actual = {
        "isolation": provider.get("isolation", "unspecified"),
        "network": provider.get("network", "unspecified"),
        "privileged": bool(provider.get("privileged", False)),
        "evidence_outputs": sorted(provider.get("evidence_outputs", []) or []),
        "execution_modes": sorted(provider.get("execution_modes", []) or []),
        "risk": provider.get("risk") or provider.get("risk_level"),
    }
    expected = semantics_from_capability(capability_spec)
    violations = []

    if expected["allowed_isolations"] and actual["isolation"] not in expected["allowed_isolations"]:
        violations.append("isolation_not_allowed")
    if expected["allowed_networks"] and actual["network"] not in expected["allowed_networks"]:
        violations.append("network_not_allowed")
    if expected["allowed_execution_modes"] and not set(actual["execution_modes"]).intersection(expected["allowed_execution_modes"]):
        violations.append("execution_mode_not_supported")
    if expected["evidence_outputs"] and not set(expected["evidence_outputs"]).issubset(actual["evidence_outputs"]):
        violations.append("required_evidence_not_produced")
    if expected["risk"] and actual["risk"] and actual["risk"] != expected["risk"]:
        violations.append("provider_risk_differs")
    if expected["requires_approval"] and not capability_spec.get("requires_approval", False):
        violations.append("approval_metadata_invalid")

    return {
        "capability": capability,
        "compatible": not violations,
        "violations": violations,
        "expected": expected,
        "actual": actual,
        "interface": interface.get("type"),
    }
