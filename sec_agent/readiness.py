"""Runtime readiness checks for registry-declared providers."""
from __future__ import annotations

import os
import socket
import urllib.parse
from typing import Any

from .discovery import discover_runtime\nfrom .integration_checks import check_mcp_environment, provider_api_check


def _env_ready(model: dict[str, Any]) -> bool:
    env = model.get("env")
    return not env or bool(os.environ.get(env))


def _endpoint_ready(endpoint: str | None, timeout: float = 0.5) -> tuple[bool, str]:
    if not endpoint:
        return True, "no endpoint declared"
    if endpoint.startswith("local:"):
        return True, "local endpoint requires provider-specific health check"
    parsed = urllib.parse.urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
    if parsed.hostname is None:
        return False, "invalid endpoint"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True, "endpoint reachable"
    except OSError as exc:
        return False, str(exc)


def check_provider_readiness(
    provider_id: str,
    provider: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, Any]:
    interface = provider.get("interface", {}) or {}
    kind = interface.get("type")

    if kind == "tool":
        result = runtime["tools"].get(provider_id, {})
        return {
            "ready": bool(result.get("available")),
            "checks": [{"name": "executable", "ready": bool(result.get("available")), "detail": result.get("path") or "not found"}],
        }

    if kind == "api":
        result = runtime["compute"].get(provider_id, {})
        endpoint = interface.get("endpoint")
        if result:
            ready = bool(result.get("available"))
            return {
                "ready": ready,
                "checks": [{"name": "provider", "ready": ready, "detail": result.get("executable") or "provider not discovered"}],
            }
        ready, detail = _endpoint_ready(endpoint)
        return {
            "ready": ready,
            "checks": [{"name": "endpoint", "ready": ready, "detail": detail}],
        }

    if kind == "mcp":
        # MCP transport/server discovery is integration-specific; registry presence
        # is retained separately from runtime connectivity.
        return {
            "ready": False,
            "checks": [{"name": "mcp_connection", "ready": False, "detail": "MCP connection requires a configured integration"}],
        }

    return {"ready": False, "checks": [{"name": "interface", "ready": False, "detail": "unsupported interface"}]}


def check_model_readiness(model: dict[str, Any]) -> dict[str, Any]:
    ready = _env_ready(model)
    return {
        "ready": ready,
        "checks": [{
            "name": "credential",
            "ready": ready,
            "detail": "credential available" if ready else f"missing {model.get('env')}",
        }],
    }


def assess_readiness(registry: dict[str, Any]) -> dict[str, Any]:
    """Build an ephemeral readiness report; never mutate the registry."""
    runtime = discover_runtime(registry)
    providers = {}
    for provider_id, provider in (registry.get("providers") or {}).items():
        providers[provider_id] = check_provider_readiness(provider_id, provider, runtime, list((registry.get("integrations") or {}).values()))

    models = {
        model_id: check_model_readiness(model)
        for model_id, model in (registry.get("models") or {}).items()
    }
    return {
        "providers": providers,
        "models": models,
        "runtime": runtime,
    }
