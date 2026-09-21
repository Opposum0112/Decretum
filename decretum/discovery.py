"""Local runtime discovery for Decretum capability providers and harnesses."""
from __future__ import annotations

import shutil
import subprocess
from typing import Any


def discover_tools(registry: dict[str, Any]) -> dict[str, Any]:
    """Discover registered tool providers without mutating the canonical registry."""
    discovered = {}
    for provider_id, provider in (registry.get("providers") or {}).items():
        interface = provider.get("interface", {}) or {}
        if interface.get("type") != "tool":
            continue
        executable = interface.get("executable")
        path = shutil.which(executable) if executable else None
        discovered[provider_id] = {
            "provider": provider_id,
            "type": "tool",
            "executable": executable,
            "path": path,
            "available": bool(path),
        }
    return discovered


def discover_harnesses(registry: dict[str, Any]) -> dict[str, Any]:
    """Discover optional locally installed harness CLIs."""
    candidates = {
        "codex": ["codex"],
        "goose": ["goose"],
        "open_code": ["opencode", "open-code"],
    }
    discovered = {}
    for harness_id, commands in candidates.items():
        configured = (registry.get("harnesses") or {}).get(harness_id)
        if not configured:
            continue
        path = next((shutil.which(command) for command in commands if shutil.which(command)), None)
        discovered[harness_id] = {
            "harness": harness_id,
            "available": bool(path),
            "executable": path,
        }
    return discovered


def discover_compute(registry: dict[str, Any]) -> dict[str, Any]:
    """Discover common local compute backends using conservative executable checks."""
    commands = {
        "docker": ["docker"],
        "podman": ["podman"],
        "lima": ["limactl"],
        "incus": ["incus"],
        "qemu": ["qemu-system-x86_64", "qemu-system-aarch64"],
        "firecracker": ["firecracker"],
    }
    discovered = {}
    for provider_id, names in commands.items():
        if provider_id not in (registry.get("providers") or {}):
            continue
        path = next((shutil.which(name) for name in names if shutil.which(name)), None)
        discovered[provider_id] = {
            "provider": provider_id,
            "available": bool(path),
            "executable": path,
        }
    return discovered


def discover_runtime(registry: dict[str, Any]) -> dict[str, Any]:
    """Return ephemeral discovery metadata; never rewrite registry.yaml."""
    return {
        "tools": discover_tools(registry),
        "harnesses": discover_harnesses(registry),
        "compute": discover_compute(registry),
    }
