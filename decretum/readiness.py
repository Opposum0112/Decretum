"""Runtime readiness checks for registry-declared providers."""
from __future__ import annotations

import os
from typing import Any

from .discovery import discover_runtime
from .integration_checks import check_mcp_environment, provider_api_check


def check_provider_readiness(
    provider_id: str,
    provider: dict[str, Any],
    runtime: dict[str, Any],
    registry_integrations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    interface = provider.get("interface", {}) or {}
    kind = interface.get("type")

    if kind == "tool":
        result = runtime["tools"].get(provider_id, {})
        ready = bool(result.get("available"))
        return {"ready": ready, "checks": [{
            "name": "executable", "ready": ready,
            "detail": result.get("path") or "not found",
        }]}

    if kind == "api":
        result = runtime["compute"].get(provider_id, {})
        if result:
            ready = bool(result.get("available"))
            return {"ready": ready, "checks": [{
                "name": "provider", "ready": ready,
                "detail": result.get("executable") or "provider not discovered",
            }]}
        ready, detail = provider_api_check(provider)
        return {"ready": ready, "checks": [{
            "name": "api", "ready": ready, "detail": detail,
        }]}

    if kind == "mcp":
        integration = next(
            (item for item in (registry_integrations or [])
             if item.get("provider") == provider_id),
            None,
        )
        ready, detail = check_mcp_environment(interface, integration)
        return {"ready": ready, "checks": [{
            "name": "mcp_connection", "ready": ready, "detail": detail,
        }]}

    return {"ready": False, "checks": [{
        "name": "interface", "ready": False, "detail": "unsupported interface",
    }]}


def check_model_readiness(model: dict[str, Any]) -> dict[str, Any]:
    env = model.get("env")
    ready = not env or bool(os.environ.get(env))
    return {"ready": ready, "checks": [{
        "name": "credential",
        "ready": ready,
        "detail": "credential available" if ready else f"missing {env}",
    }]}


def assess_readiness(registry: dict[str, Any]) -> dict[str, Any]:
    """Build an ephemeral readiness report; never mutate the registry."""
    runtime = discover_runtime(registry)
    integrations = list((registry.get("integrations") or {}).values())
    providers = {
        provider_id: check_provider_readiness(
            provider_id, provider, runtime, integrations
        )
        for provider_id, provider in (registry.get("providers") or {}).items()
    }
    models = {
        model_id: check_model_readiness(model)
        for model_id, model in (registry.get("models") or {}).items()
    }
    return {"providers": providers, "models": models, "runtime": runtime}
