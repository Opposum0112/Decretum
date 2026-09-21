"""Discover host execution surfaces without mutating the canonical ontology.

Discovery answers: "what can this host execute, through which interface, and with
which declared harnesses?" It deliberately does not infer new security semantics
from executable names and never edits the canonical LinkML schema.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

from .validator import DEFAULT_PROVIDER_REGISTRY, load_provider_registry


HARNESS_EXECUTABLES = {
    "codex": "codex",
    "goose": "goose",
    "open_code": "opencode",
}


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _tool_ready(provider: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    interface = provider.get("interface", {}) or {}
    executable = interface.get("executable")
    if not executable:
        return False, {"method": "executable", "available": False, "reason": "no executable declared"}
    path = shutil.which(str(executable))
    return bool(path), {
        "method": "executable",
        "executable": executable,
        "path": path,
        "available": bool(path),
    }


def _integration_ready(integration_id: str, integration: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """Use conservative, local-only probes for registered integrations."""
    env_name = "DECRETUM_" + "".join(c if c.isalnum() else "_" for c in integration_id.upper()) + "_AVAILABLE"
    if os.environ.get(env_name) == "1":
        return True, {"method": "environment", "environment": env_name, "available": True}

    provider = integration.get("provider")
    command_by_provider = {
        "docker": "docker",
        "podman": "podman",
        "lima": "limactl",
        "incus": "incus",
        "local-process": "sh",
    }
    command = command_by_provider.get(str(provider))
    if command:
        path = shutil.which(command)
        return bool(path), {
            "method": "executable",
            "executable": command,
            "path": path,
            "available": bool(path),
        }

    # MCP/API endpoints may require credentials or a running service. Discovery
    # must not make network calls merely to decide whether a surface exists.
    return False, {
        "method": "declarative",
        "available": False,
        "reason": "no safe local probe; integration is registered but not verified",
    }


def _harness_surface(harness_id: str, harness: dict[str, Any]) -> dict[str, Any]:
    executable = HARNESS_EXECUTABLES.get(harness_id)
    path = shutil.which(executable) if executable else None
    configured = os.environ.get(
        "DECRETUM_HARNESS_" + "".join(c if c.isalnum() else "_" for c in harness_id.upper()) + "_AVAILABLE"
    ) == "1"
    available = bool(path or configured)
    return {
        "harness": harness_id,
        "available": available,
        "verification": {
            "executable": executable,
            "path": path,
            "environment_override": configured,
        },
        "supported_interfaces": harness.get("supported_interfaces", []) or [],
    }


def discover_capability_surfaces(
    registry_path: Path = DEFAULT_PROVIDER_REGISTRY,
    recipe: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = load_provider_registry(str(registry_path))
    providers = registry.get("providers", {}) or {}
    integrations = registry.get("integrations", {}) or {}
    harnesses = registry.get("harnesses", {}) or {}

    harness_surfaces = {
        hid: _harness_surface(hid, spec)
        for hid, spec in sorted(harnesses.items())
    }

    surfaces: list[dict[str, Any]] = []
    for provider_id, provider in sorted(providers.items()):
        interface = provider.get("interface", {}) or {}
        interface_type = interface.get("type")
        if interface_type == "tool":
            available, verification = _tool_ready(provider)
            integration_id = next(
                (iid for iid, item in integrations.items() if item.get("provider") == provider_id),
                None,
            )
            integration_ready = None
            if integration_id:
                integration_ready, _ = _integration_ready(integration_id, integrations[integration_id])
            harness_list = [
                hid for hid, hs in harness_surfaces.items()
                if hs["available"] and interface_type in hs["supported_interfaces"]
            ]
            ready = available and bool(harness_list)
        else:
            integration_id = next(
                (iid for iid, item in integrations.items() if item.get("provider") == provider_id),
                None,
            )
            if integration_id:
                available, verification = _integration_ready(integration_id, integrations[integration_id])
            else:
                available, verification = False, {
                    "method": "declarative",
                    "available": False,
                    "reason": "provider has no registered integration",
                }
            harness_list = [
                hid for hid, hs in harness_surfaces.items()
                if hs["available"] and interface_type in hs["supported_interfaces"]
            ]
            ready = available and bool(harness_list)

        for capability in provider.get("capabilities", []) or []:
            surfaces.append({
                "capability": capability,
                "provider": provider_id,
                "interface": interface_type,
                "available": available,
                "ready": ready,
                "harnesses": harness_list,
                "integrations": [integration_id] if integration_id else [],
                "verification": verification,
                "execution_modes": provider.get("execution_modes", []) or [],
                "isolation": provider.get("isolation"),
                "network": provider.get("network"),
            })

    registered = {
        cap
        for provider in providers.values()
        for cap in (provider.get("capabilities", []) or [])
    }
    requested = set()
    if recipe:
        for cap in recipe.get("capability_catalog", []) or []:
            if isinstance(cap, dict) and cap.get("id"):
                requested.add(cap["id"])
        for step in recipe.get("experiments", []) or []:
            if isinstance(step, dict):
                requested.update(step.get("capabilities", []) or [])
                if step.get("capability"):
                    requested.add(step["capability"])

    candidates = []
    for capability in sorted(requested - registered):
        candidates.append({
            "capability": capability,
            "kind": "candidate",
            "status": "review_required",
            "reason": "referenced by recipe but absent from canonical provider registry",
            "proposal": {
                "id": capability,
                "description": "Human-authored semantic definition required; discovery does not infer security semantics.",
                "providers": [],
                "approval_required": True,
            },
        })

    result = {
        "api_version": "decretum.dev/v1",
        "kind": "CapabilitySurfaceDiscovery",
        "registry": {
            "source": str(registry_path),
            "digest": _digest(registry),
        },
        "harnesses": harness_surfaces,
        "surfaces": surfaces,
        "candidates": candidates,
    }
    result["digest"] = _digest(result)
    return result


def write_discovery_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "capability-surface-manifest.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_candidate_yaml(report: dict[str, Any], output_dir: Path) -> Path | None:
    if not report.get("candidates"):
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "capability-candidates.yaml"
    payload = {
        "apiVersion": "decretum.dev/v1",
        "kind": "CapabilityCandidateSet",
        "candidates": report["candidates"],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path
