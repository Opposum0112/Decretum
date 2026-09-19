"""Portable handoff adapters for external harness runtimes.

These adapters never execute a harness. They validate/select the handoff
protocol so a separate runtime can consume the compiled contract.
"""
from __future__ import annotations

from typing import Any

from .harness import HarnessAdapter


class RegistryHarnessAdapter(HarnessAdapter):
    """Represent an external harness without embedding its runtime."""

    def __init__(self, harness_id: str):
        self.id = harness_id

    def supports(self, contract: dict[str, Any]) -> bool:
        if contract.get("kind") != "ResearchExecutionContract":
            return False
        if contract.get("handoff", {}).get("target") != "external_harness_runtime":
            return False
        selected = contract.get("execution", {}).get("harness")
        return selected == self.id or self.id in contract.get("execution", {}).get("resolution", {}).get("harnesses", [])

    def prepare(self, contract: dict[str, Any]) -> dict[str, Any]:
        if not self.supports(contract):
            raise ValueError(f"contract is not ready for external harness {self.id!r}")
        return {
            "protocol": "decretum.dev/v1",
            "type": "research_execution_handoff",
            "adapter": self.id,
            "contract_id": contract["contract_id"],
            "contract": contract,
            "execution": "external_harness_runtime",
            "decretum_action": "none_after_handoff",
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
        raise ValueError(f"unsupported external harness: {harness_id!r}") from exc


def available_adapters() -> list[str]:
    return sorted(ADAPTERS)
