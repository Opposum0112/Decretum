"""Harness adapter registry and portable adapter implementations.

These adapters intentionally do not execute agent runtimes. They only translate
Decretum's portable execution contract into a stable hand-off envelope that a
native harness integration can consume.
"""
from __future__ import annotations

from typing import Any

from .harness import HarnessAdapter


class RegistryHarnessAdapter(HarnessAdapter):
    """Base adapter for a registry-declared harness."""

    def __init__(self, harness_id: str):
        self.id = harness_id

    def supports(self, contract: dict[str, Any]) -> bool:
        resolution = contract.get("resolution", {})
        return any(
            binding.get("harness") == self.id and binding.get("available", False)
            for binding in resolution.get("bindings", [])
        )

    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        if not self.supports(contract):
            raise ValueError(f"contract has no ready binding for harness {self.id!r}")
        bindings = [
            binding for binding in contract["resolution"]["bindings"]
            if binding.get("harness") == self.id
        ]
        return {
            "protocol": "decretum.dev/v1",
            "adapter": self.id,
            "contract_id": contract["contract_id"],
            "research": contract["research"],
            "environment": contract["environment"],
            "experiment_graph": contract["experiment_graph"],
            "bindings": bindings,
            "policy": contract["policy"],
            "evidence": contract["evidence"],
            "completion": contract["completion"],
        }


class CodexAdapter(RegistryHarnessAdapter):
    def __init__(self):
        super().__init__("codex")


class GooseAdapter(RegistryHarnessAdapter):
    def __init__(self):
        super().__init__("goose")


class GoogleAdkAdapter(RegistryHarnessAdapter):
    def __init__(self):
        super().__init__("google_adk")


class OpenCodeAdapter(RegistryHarnessAdapter):
    def __init__(self):
        super().__init__("open_code")


class VercelAIAdapter(RegistryHarnessAdapter):
    def __init__(self):
        super().__init__("vercel_ai")


ADAPTERS: dict[str, type[RegistryHarnessAdapter]] = {
    "codex": CodexAdapter,
    "goose": GooseAdapter,
    "google_adk": GoogleAdkAdapter,
    "open_code": OpenCodeAdapter,
    "vercel_ai": VercelAIAdapter,
}


def get_adapter(harness_id: str) -> HarnessAdapter:
    try:
        return ADAPTERS[harness_id]()
    except KeyError as exc:
        raise ValueError(f"unsupported harness adapter: {harness_id!r}") from exc


def available_adapters() -> list[str]:
    return sorted(ADAPTERS)
