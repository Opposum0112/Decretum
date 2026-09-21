"""Provider-specific MCP/API readiness adapters.

Checks are intentionally conservative: connectivity is verified, but credentials
and remote service semantics are never inferred from reachability alone.
"""
from __future__ import annotations

import os
import socket
import urllib.parse
from typing import Any


def _url(endpoint: str) -> tuple[str, int, str]:
    parsed = urllib.parse.urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    if not parsed.hostname:
        raise ValueError("endpoint has no hostname")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.hostname, port, parsed.scheme


def check_tcp(endpoint: str, timeout: float = 0.75) -> tuple[bool, str]:
    host, port, _ = _url(endpoint)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"TCP {host}:{port} reachable"
    except OSError as exc:
        return False, f"TCP connection failed: {exc}"


def check_http(endpoint: str, timeout: float = 1.5) -> tuple[bool, str]:
    host, port, scheme = _url(endpoint)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"{scheme.upper()} endpoint {host}:{port} reachable"
    except OSError as exc:
        return False, f"HTTP endpoint unreachable: {exc}"


def check_mcp_environment(interface: dict[str, Any], integration: dict[str, Any] | None) -> tuple[bool, str]:
    """Check configured MCP transport metadata without opening an MCP session."""
    if not integration:
        return False, "no MCP integration configured"
    transport = integration.get("transport") or interface.get("transport")
    if transport in {"stdio", "local"}:
        command = integration.get("command") or interface.get("command")
        if not command:
            return False, "MCP stdio integration has no command"
        return True, "MCP stdio command configured"
    endpoint = integration.get("endpoint") or interface.get("endpoint")
    if endpoint:
        return check_tcp(endpoint)
    return False, "MCP integration has no endpoint or command"


def provider_api_check(provider: dict[str, Any]) -> tuple[bool, str]:
    interface = provider.get("interface", {}) or {}
    endpoint = interface.get("endpoint")
    if not endpoint:
        return False, "API provider has no endpoint"
    if endpoint.startswith("local:"):
        return False, "local API requires provider-specific integration configuration"
    return check_http(endpoint)


def credential_check(env_name: str | None) -> tuple[bool, str]:
    if not env_name:
        return True, "no credential configured"
    if os.environ.get(env_name):
        return True, f"{env_name} is set"
    return False, f"missing {env_name}"
