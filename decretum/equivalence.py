"""Capability equivalence and safe provider substitution."""
from __future__ import annotations

from typing import Any


def provider_semantics(provider: dict[str, Any], capability: str) -> dict[str, Any]:
    interface = provider.get("interface", {}) or {}
    return {
        "capability": capability,
        "interface": interface.get("type"),
        "isolation": provider.get("isolation", "unspecified"),
        "network": provider.get("network", "unspecified"),
        "privileged": bool(provider.get("privileged", False)),
        "evidence_outputs": sorted(provider.get("evidence_outputs", []) or []),
        "execution_modes": sorted(provider.get("execution_modes", []) or []),
        "risk": provider.get("risk") or provider.get("risk_level"),
    }


def equivalence(provider_a: dict[str, Any], provider_b: dict[str, Any], capability: str) -> dict[str, Any]:
    a = provider_semantics(provider_a, capability)
    b = provider_semantics(provider_b, capability)
    differences = {}
    for key in ("isolation", "network", "privileged", "evidence_outputs", "execution_modes", "risk"):
        if a[key] != b[key]:
            differences[key] = {"a": a[key], "b": b[key]}
    equivalent = not differences
    return {
        "equivalent": equivalent,
        "capability": capability,
        "differences": differences,
        "reason": "same declared execution semantics" if equivalent else "execution semantics differ",
    }


def annotate_equivalence(
    selected: dict[str, Any],
    fallback: dict[str, Any],
    capability: str,
) -> dict[str, Any]:
    result = equivalence(selected, fallback, capability)
    return {
        **fallback,
        "equivalence": result,
        "safe_fallback": result["equivalent"],
    }
